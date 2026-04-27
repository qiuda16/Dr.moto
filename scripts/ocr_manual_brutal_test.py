import argparse
import concurrent.futures
import json
import os
import statistics
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

import requests


def now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if p <= 0:
        return sorted_values[0]
    if p >= 1:
        return sorted_values[-1]
    idx = int(round((len(sorted_values) - 1) * p))
    return float(sorted_values[idx])


class PipelineError(Exception):
    pass


class OcrBrutalRunner:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        store_id: str,
        model_id: int,
        timeout_seconds: int,
        parse_timeout_seconds: int,
        parse_stall_seconds: int,
        parse_poll_seconds: float,
        cleanup_source_document: bool,
        resume_on_stall: bool,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.store_id = store_id
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.parse_timeout_seconds = parse_timeout_seconds
        self.parse_stall_seconds = parse_stall_seconds
        self.parse_poll_seconds = parse_poll_seconds
        self.cleanup_source_document = cleanup_source_document
        self.resume_on_stall = resume_on_stall
        self._local = threading.local()

    def _session(self) -> requests.Session:
        sess = getattr(self._local, "session", None)
        if sess is None:
            sess = requests.Session()
            setattr(self._local, "session", sess)
        return sess

    def _auth_headers(self) -> dict[str, str]:
        token = getattr(self._local, "token", "")
        if not token:
            sess = self._session()
            resp = sess.post(
                f"{self.base_url}/auth/token",
                data={"username": self.username, "password": self.password},
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            token = (resp.json() or {}).get("access_token") or ""
            if not token:
                raise PipelineError("auth token missing")
            setattr(self._local, "token", token)
        return {"Authorization": f"Bearer {token}", "X-Store-Id": self.store_id}

    def _request(
        self,
        method: str,
        path: str,
        *,
        retries: int = 1,
        retry_wait: float = 0.8,
        **kwargs: Any,
    ) -> requests.Response:
        last_exc: Exception | None = None
        for i in range(retries + 1):
            try:
                headers = kwargs.pop("headers", {}) or {}
                merged = {}
                merged.update(self._auth_headers())
                merged.update(headers)
                resp = self._session().request(
                    method=method.upper(),
                    url=f"{self.base_url}{path}",
                    headers=merged,
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                if resp.status_code in {401, 403} and i < retries:
                    setattr(self._local, "token", "")
                    time.sleep(retry_wait)
                    continue
                return resp
            except Exception as exc:
                last_exc = exc
                if i < retries:
                    time.sleep(retry_wait)
                    continue
                raise
        raise last_exc or RuntimeError("request failed")

    def _pick_model(self) -> dict[str, Any]:
        resp = self._request("GET", f"/mp/catalog/vehicle-models?page=1&page_size=5", retries=2)
        resp.raise_for_status()
        payload = resp.json() or {}
        items = payload.get("items") or []
        for row in items:
            if int(row.get("id") or 0) == self.model_id:
                return row
        return {}

    def _get_parse_job(self, job_id: int) -> dict[str, Any]:
        resp = self._request("GET", f"/mp/knowledge/parse-jobs/{job_id}", retries=1)
        resp.raise_for_status()
        return resp.json() or {}

    def _resume_parse_job(self, job_id: int) -> dict[str, Any]:
        resp = self._request("POST", f"/mp/knowledge/parse-jobs/{job_id}/resume", retries=1)
        resp.raise_for_status()
        return resp.json() or {}

    def _retry_parse_job(self, job_id: int) -> dict[str, Any]:
        resp = self._request("POST", f"/mp/knowledge/parse-jobs/{job_id}/retry", retries=1)
        resp.raise_for_status()
        return resp.json() or {}

    def _wait_parse_job(self, job_id: int) -> dict[str, Any]:
        started = time.time()
        last_progress_marker: Optional[Tuple[Any, ...]] = None
        last_progress_at = started
        resume_attempts = 0
        while True:
            payload = self._get_parse_job(job_id)
            now = time.time()
            elapsed = now - started
            status = str(payload.get("status") or "").strip().lower()
            progress_marker = (
                status,
                int(payload.get("processed_batches") or 0),
                int(payload.get("total_batches") or 0),
                int(payload.get("progress_percent") or 0),
                str(payload.get("updated_at") or ""),
                bool(payload.get("summary_json")),
                bool(payload.get("raw_result_json")),
            )
            if progress_marker != last_progress_marker:
                last_progress_marker = progress_marker
                last_progress_at = now
            if status == "completed":
                return payload
            if status == "failed":
                if self.resume_on_stall:
                    retried = self._retry_parse_job(job_id)
                    new_job_id = int(retried.get("id") or 0)
                    if new_job_id and new_job_id != job_id:
                        job_id = new_job_id
                        started = now
                        last_progress_marker = None
                        last_progress_at = now
                        resume_attempts = 0
                        continue
                err = payload.get("error_message") or "unknown parse failure"
                raise PipelineError(f"parse failed job_id={job_id}: {err}")
            if self.parse_timeout_seconds > 0 and elapsed > self.parse_timeout_seconds:
                raise PipelineError(f"parse timeout job_id={job_id} after {self.parse_timeout_seconds}s")
            stalled_for = now - last_progress_at
            if self.parse_stall_seconds > 0 and stalled_for > self.parse_stall_seconds:
                if self.resume_on_stall and resume_attempts < 3:
                    resumed = self._resume_parse_job(job_id)
                    resumed_job_id = int(resumed.get("id") or 0) or job_id
                    job_id = resumed_job_id
                    last_progress_marker = None
                    last_progress_at = now
                    resume_attempts += 1
                    continue
                progress_text = payload.get("progress_message") or "no progress message"
                raise PipelineError(
                    f"parse stalled job_id={job_id} for {int(stalled_for)}s at "
                    f"{payload.get('processed_batches') or 0}/{payload.get('total_batches') or 0}: {progress_text}"
                )
            time.sleep(self.parse_poll_seconds)

    def _start_new_parse(self, case_id: str, pdf_path: Path, metrics: dict[str, Any]) -> tuple[int, float]:
        up0 = time.time()
        with pdf_path.open("rb") as fp:
            files = {"file": (pdf_path.name, fp, "application/pdf")}
            data = {
                "title": f"[Stress]{case_id}-{pdf_path.stem}",
                "category": "维修手册",
                "notes": "ocr_brutal_test",
            }
            resp = self._request(
                "POST",
                f"/mp/knowledge/catalog-models/{self.model_id}/documents",
                files=files,
                data=data,
                retries=0,
            )
        if resp.status_code != 200:
            raise PipelineError(f"upload failed: {resp.status_code} {resp.text[:200]}")
        upload_payload = resp.json() or {}
        doc_id = int(upload_payload.get("id") or 0)
        if not doc_id:
            raise PipelineError("upload succeeded but document id missing")
        metrics["ids"]["document_id"] = doc_id
        metrics["durations"]["upload_seconds"] = round(time.time() - up0, 3)

        parse0 = time.time()
        resp = self._request("POST", f"/mp/knowledge/documents/{doc_id}/parse", retries=1)
        if resp.status_code != 200:
            raise PipelineError(f"parse start failed: {resp.status_code} {resp.text[:200]}")
        parse_payload = resp.json() or {}
        job_id = int(parse_payload.get("id") or 0)
        if not job_id:
            raise PipelineError("parse start succeeded but job id missing")
        metrics["ids"]["job_id"] = job_id
        metrics["counts"]["parse_mode"] = "fresh_upload"
        return doc_id, parse0

    def _attach_existing_parse(self, job_id: int, metrics: dict[str, Any]) -> Tuple[Optional[int], float]:
        parse0 = time.time()
        detail = self._get_parse_job(job_id)
        metrics["ids"]["job_id"] = int(detail.get("id") or job_id)
        doc_id = int(detail.get("document_id") or 0) or None
        if doc_id:
            metrics["ids"]["document_id"] = doc_id
        metrics["counts"]["parse_mode"] = "existing_job"
        return doc_id, parse0

    def run_one(self, case_id: str, pdf_path: Path, existing_job_id: Optional[int] = None) -> dict[str, Any]:
        t0 = time.time()
        metrics: dict[str, Any] = {
            "case_id": case_id,
            "pdf_path": str(pdf_path),
            "ok": False,
            "error": "",
            "durations": {},
            "ids": {},
            "counts": {},
            "status_trace": [],
        }
        if not existing_job_id and not pdf_path.exists():
            metrics["error"] = f"pdf missing: {pdf_path}"
            return metrics

        doc_id = None
        try:
            if existing_job_id:
                doc_id, parse0 = self._attach_existing_parse(existing_job_id, metrics)
                job_id = int(metrics["ids"]["job_id"])
            else:
                doc_id, parse0 = self._start_new_parse(case_id, pdf_path, metrics)
                job_id = int(metrics["ids"]["job_id"])

            detail = self._wait_parse_job(job_id)
            metrics["durations"]["parse_total_seconds"] = round(time.time() - parse0, 3)
            metrics["ids"]["job_id"] = int(detail.get("id") or job_id)
            if detail.get("document_id"):
                metrics["ids"]["document_id"] = int(detail.get("document_id") or 0)
            metrics["status_trace"].append(str(detail.get("status") or ""))
            pages = detail.get("pages") or []
            summary = detail.get("summary_json") or {}
            metrics["counts"]["parsed_pages"] = len(pages)
            metrics["counts"]["summary_specs"] = len(summary.get("specs") or [])
            metrics["counts"]["summary_procedures"] = len(summary.get("procedures") or [])
            metrics["counts"]["summary_sections"] = len(summary.get("sections") or [])

            bind0 = time.time()
            resp = self._request("POST", f"/mp/knowledge/parse-jobs/{job_id}/bind-catalog-model", retries=1)
            bind_payload = {}
            if resp.status_code == 200:
                bind_payload = resp.json() or {}
                target_model_id = int(((bind_payload.get("model") or {}).get("id")) or self.model_id)
                metrics["counts"]["bound_model_created"] = bool(bind_payload.get("created"))
                metrics["counts"]["bind_mode"] = "auto_bind"
            else:
                # Fallback: OCR may not always infer stable make/model; bind to current catalog model explicitly.
                fallback_resp = self._request(
                    "PATCH",
                    f"/mp/knowledge/documents/{doc_id}/catalog-confirmation",
                    json={"action": "bind_existing", "model_id": self.model_id, "notes": "ocr_brutal_test_fallback_bind"},
                    retries=1,
                )
                if fallback_resp.status_code != 200:
                    raise PipelineError(f"bind model failed: {resp.status_code} {resp.text[:200]}")
                fallback_payload = fallback_resp.json() or {}
                target_model_id = int(fallback_payload.get("model_id") or self.model_id)
                metrics["counts"]["bound_model_created"] = False
                metrics["counts"]["bind_mode"] = "fallback_bind_existing"
            metrics["ids"]["bound_model_id"] = target_model_id
            metrics["durations"]["bind_model_seconds"] = round(time.time() - bind0, 3)

            import0 = time.time()
            resp = self._request("POST", f"/mp/knowledge/parse-jobs/{job_id}/import-confirmed-specs", retries=1)
            if resp.status_code != 200:
                raise PipelineError(f"import specs failed: {resp.status_code} {resp.text[:200]}")
            import_payload = resp.json() or {}
            metrics["counts"]["imported_specs"] = int(import_payload.get("imported") or 0)
            metrics["durations"]["import_specs_seconds"] = round(time.time() - import0, 3)

            seg0 = time.time()
            resp = self._request("POST", f"/mp/knowledge/parse-jobs/{job_id}/materialize-segments", retries=1)
            if resp.status_code == 200:
                seg_payload = resp.json() or {}
                metrics["counts"]["materialized_segments"] = int(seg_payload.get("materialized") or 0)
                metrics["counts"]["materialize_mode"] = "normal"
            else:
                # Some manuals (especially short/flat PDFs) do not produce toc_segments; treat as soft pass.
                resp_text = resp.text or ""
                if resp.status_code == 400 and ("目录分段" in resp_text or "toc" in resp_text.lower()):
                    metrics["counts"]["materialized_segments"] = 0
                    metrics["counts"]["materialize_mode"] = "soft_skip_no_toc"
                else:
                    raise PipelineError(f"materialize segments failed: {resp.status_code} {resp.text[:200]}")
            metrics["durations"]["materialize_segments_seconds"] = round(time.time() - seg0, 3)

            sync0 = time.time()
            resp = self._request("POST", f"/mp/catalog/vehicle-models/{target_model_id}/service-items/sync-manual-parts", retries=1)
            if resp.status_code != 200:
                raise PipelineError(f"sync manual parts failed: {resp.status_code} {resp.text[:200]}")
            sync_payload = resp.json() or {}
            metrics["counts"]["service_items_synced"] = int(sync_payload.get("synced") or 0)
            metrics["durations"]["sync_manual_parts_seconds"] = round(time.time() - sync0, 3)

            metrics["ok"] = True
            return metrics
        except Exception as exc:
            metrics["error"] = str(exc)
            return metrics
        finally:
            metrics["durations"]["total_seconds"] = round(time.time() - t0, 3)
            if self.cleanup_source_document and doc_id:
                try:
                    self._request("DELETE", f"/mp/knowledge/documents/{doc_id}", retries=0)
                except Exception:
                    pass


def run_batch(
    runner: OcrBrutalRunner,
    *,
    label: str,
    pdf_path: Path,
    rounds: int,
    workers: int,
    existing_job_id: Optional[int] = None,
) -> dict[str, Any]:
    if rounds <= 0:
        return {
            "label": label,
            "rounds": 0,
            "workers": workers,
            "results": [],
            "summary": {"total": 0, "ok": 0, "fail": 0, "pass_rate": 0.0},
        }

    results: list[dict[str, Any]] = []
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = []
        for i in range(rounds):
            case_id = f"{label}-{i+1:03d}"
            futures.append(pool.submit(runner.run_one, case_id, pdf_path, existing_job_id))
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    total = len(results)
    ok = sum(1 for row in results if row.get("ok"))
    fail = total - ok
    durations = sorted(float((row.get("durations") or {}).get("total_seconds") or 0.0) for row in results if row.get("ok"))
    err_counter: dict[str, int] = {}
    for row in results:
        if row.get("ok"):
            continue
        reason = str(row.get("error") or "unknown")
        key = reason[:160]
        err_counter[key] = err_counter.get(key, 0) + 1

    summary = {
        "total": total,
        "ok": ok,
        "fail": fail,
        "pass_rate": round((ok / total) * 100, 2) if total else 0.0,
        "wall_clock_seconds": round(time.time() - start, 3),
        "p50_seconds": round(percentile(durations, 0.5), 3) if durations else 0.0,
        "p90_seconds": round(percentile(durations, 0.9), 3) if durations else 0.0,
        "p95_seconds": round(percentile(durations, 0.95), 3) if durations else 0.0,
        "avg_seconds": round(statistics.fmean(durations), 3) if durations else 0.0,
        "error_counter": err_counter,
    }
    return {
        "label": label,
        "pdf_path": str(pdf_path),
        "rounds": rounds,
        "workers": workers,
        "results": results,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Brutal test OCR manual + downstream pipeline.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="change_me_now")
    parser.add_argument("--store-id", default="default")
    parser.add_argument("--model-id", type=int, default=150)
    parser.add_argument("--quick-pdf", default="Ducati_Monster_Manual_Mock.pdf")
    parser.add_argument("--quick-rounds", type=int, default=8)
    parser.add_argument("--quick-workers", type=int, default=4)
    parser.add_argument("--real-pdf", default="1.pdf")
    parser.add_argument("--real-rounds", type=int, default=1)
    parser.add_argument("--real-workers", type=int, default=1)
    parser.add_argument("--request-timeout-seconds", type=int, default=90)
    parser.add_argument("--parse-timeout-seconds", type=int, default=0)
    parser.add_argument("--parse-stall-seconds", type=int, default=900)
    parser.add_argument("--parse-poll-seconds", type=float, default=2.0)
    parser.add_argument("--resume-on-stall", action="store_true")
    parser.add_argument("--existing-job-id", type=int, default=0)
    parser.add_argument("--cleanup-source-document", action="store_true")
    parser.add_argument("--report-dir", default="docs/recovery_reports")
    args = parser.parse_args()

    workspace = Path(".").resolve()
    report_dir = (workspace / args.report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    runner = OcrBrutalRunner(
        base_url=args.base_url,
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        model_id=args.model_id,
        timeout_seconds=args.request_timeout_seconds,
        parse_timeout_seconds=args.parse_timeout_seconds,
        parse_stall_seconds=max(0, args.parse_stall_seconds),
        parse_poll_seconds=max(0.5, args.parse_poll_seconds),
        cleanup_source_document=bool(args.cleanup_source_document),
        resume_on_stall=bool(args.resume_on_stall),
    )
    model_info = {}
    try:
        model_info = runner._pick_model()
    except Exception:
        model_info = {}

    quick_pdf_path = (workspace / args.quick_pdf).resolve()
    real_pdf_path = (workspace / args.real_pdf).resolve()

    batches: list[dict[str, Any]] = []
    batches.append(
        run_batch(
            runner,
            label="quick",
            pdf_path=quick_pdf_path,
            rounds=max(0, args.quick_rounds),
            workers=max(1, args.quick_workers),
        )
    )
    if args.real_rounds > 0 and real_pdf_path.exists():
        batches.append(
            run_batch(
                runner,
                label="real",
                pdf_path=real_pdf_path,
                rounds=max(0, args.real_rounds),
                workers=max(1, args.real_workers),
                existing_job_id=(args.existing_job_id or None),
            )
        )
    elif args.real_rounds > 0:
        batches.append(
            {
                "label": "real",
                "pdf_path": str(real_pdf_path),
                "rounds": args.real_rounds,
                "workers": args.real_workers,
                "results": [],
                "summary": {
                    "total": 0,
                    "ok": 0,
                    "fail": 0,
                    "pass_rate": 0.0,
                    "error_counter": {"real_pdf_missing": 1},
                },
            }
        )

    all_results = [row for batch in batches for row in (batch.get("results") or [])]
    total = len(all_results)
    ok = sum(1 for row in all_results if row.get("ok"))
    fail = total - ok
    overall_pass = total > 0 and fail == 0

    output = {
        "generated_at": iso_now(),
        "config": {
            "base_url": args.base_url,
            "store_id": args.store_id,
            "model_id": args.model_id,
            "model_info": model_info,
            "quick_pdf": str(quick_pdf_path),
            "quick_rounds": args.quick_rounds,
            "quick_workers": args.quick_workers,
            "real_pdf": str(real_pdf_path),
            "real_rounds": args.real_rounds,
            "real_workers": args.real_workers,
            "cleanup_source_document": bool(args.cleanup_source_document),
            "parse_timeout_seconds": args.parse_timeout_seconds,
            "parse_stall_seconds": args.parse_stall_seconds,
            "resume_on_stall": bool(args.resume_on_stall),
            "existing_job_id": args.existing_job_id or None,
        },
        "batches": batches,
        "summary": {
            "total": total,
            "ok": ok,
            "fail": fail,
            "overall_pass": overall_pass,
            "overall_pass_rate": round((ok / total) * 100, 2) if total else 0.0,
        },
    }

    json_path = report_dir / f"ocr_manual_brutal_test_{now_ts()}.json"
    md_path = report_dir / f"ocr_manual_brutal_test_{now_ts()}.md"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# OCR Manual Brutal Test",
        "",
        f"- Generated At: {output['generated_at']}",
        f"- Overall Pass: **{overall_pass}**",
        f"- Total: {total} / OK: {ok} / Fail: {fail}",
        f"- Overall Pass Rate: {output['summary']['overall_pass_rate']}%",
        "",
        "## Batches",
    ]
    for batch in batches:
        summary = batch.get("summary") or {}
        lines.append(
            f"- {batch.get('label')}: total={summary.get('total',0)} ok={summary.get('ok',0)} "
            f"fail={summary.get('fail',0)} pass_rate={summary.get('pass_rate',0)}% "
            f"p95={summary.get('p95_seconds',0)}s"
        )
        errors = summary.get("error_counter") or {}
        if errors:
            lines.append(f"  errors={json.dumps(errors, ensure_ascii=False)}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "summary": output["summary"],
                "json_report": str(json_path),
                "md_report": str(md_path),
            },
            ensure_ascii=False,
        )
    )
    print(f"json_report={json_path}")
    print(f"md_report={md_path}")
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
