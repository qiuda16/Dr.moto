import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Form,
  Input,
  Layout,
  Modal,
  Space,
  Tag,
  Typography,
} from 'antd';
import axios from 'axios';

const { Header, Content } = Layout;
const { Title, Text } = Typography;
const api = axios.create({ baseURL: '/api' });
const assistantSourceTagPattern = /\[(手册原文|结构化提炼|经验\/推断)\]/g;
const CHAT_CACHE_KEY = 'cs_workspace_chat_v2';
const QUICK_PROMPTS = [
  '苏AM9371 这台车现在什么情况',
  '现在待交付的车牌号都是多少',
  '这个项目有哪些模块，数据主要分几层',
  '给我总结今天门店最该先盯的事',
];

function buildAssistantMeta(data) {
  const debug = data?.debug || {};
  const items = [];

  if (debug.write_executed) items.push({ tone: 'success', label: `已执行 ${debug.write_action || '动作'}` });
  else if (debug.write_intent_detected) items.push({ tone: 'warn', label: `待补全 ${debug.write_action || '动作'}` });
  else if (debug.knowledge_gap_fast_path) items.push({ tone: 'warn', label: '资料不足' });
  else if (debug.global_query_fast_path) items.push({ tone: 'info', label: '全局查询' });
  else if (debug.entity_intent_fast_path || debug.fact_guard_triggered) items.push({ tone: 'info', label: '业务快答' });

  if (debug.model) items.push({ tone: 'muted', label: debug.model });
  if (debug.repair_response_formatted) items.push({ tone: 'info', label: '维修回答卡' });
  if (debug.risk_level) {
    items.push({
      tone: debug.risk_level === 'low' ? 'success' : 'warn',
      label: `风险 ${debug.risk_level}`,
    });
  }
  if (Array.isArray(debug.write_missing_fields) && debug.write_missing_fields.length) {
    items.push({ tone: 'warn', label: `缺少 ${debug.write_missing_fields.join(', ')}` });
  }
  if (debug.primary_domain) items.push({ tone: 'muted', label: `域 ${debug.primary_domain}` });

  return items;
}

function normalizeAssistantLine(text) {
  return String(text || '').replace(/\s+/g, ' ').replace(/^[\d\.\)\(、\-\s]+/, '').trim();
}

function parseAssistantLine(text) {
  const raw = String(text || '').trim();
  if (!raw) return null;
  const matches = [...raw.matchAll(assistantSourceTagPattern)];
  const tag = matches.length ? matches[matches.length - 1][1] : '';
  return {
    text: raw.replace(assistantSourceTagPattern, '').trim(),
    tag,
  };
}

function sourceTagTone(tag) {
  return (
    {
      手册原文: 'primary',
      结构化提炼: 'success',
      '经验/推断': 'warn',
    }[String(tag || '').trim()] || 'muted'
  );
}

function sourceTypeLabel(type) {
  return (
    {
      customer: '客户档案',
      vehicle: '车辆档案',
      work_order: '当前工单',
      health_record: '最近体检',
      recent_work_order: '相关工单',
      knowledge: '知识库',
      knowledge_document: '标准资料',
      vehicle_catalog_model: '车型目录',
    }[String(type || '').trim()] || '参考来源'
  );
}

function buildAssistantSections(content) {
  const response = String(content || '').trim();
  if (!response) return [];
  const sections = [];
  let current = {
    key: 'summary',
    title: '关键结论/快查参数',
    description: '先看关键结论和明确字段',
    lines: [],
  };
  const pushCurrent = () => {
    if (current.lines.length) sections.push(current);
  };
  const mapHeader = (line) => {
    if (line.includes('关键结论') || line.includes('快查参数')) return ['summary', '关键结论/快查参数', '先看关键结论和明确字段'];
    if (line.includes('施工步骤') || line.includes('可执行步骤')) return ['steps', '施工步骤', '按顺序执行更稳'];
    if (line.includes('风险与缺口') || line.includes('风险提示')) return ['risks', '风险与缺口', '缺值、冲突项和复核提醒'];
    return null;
  };
  response.split('\n').forEach((line) => {
    const compact = normalizeAssistantLine(line);
    if (!compact) return;
    const header = mapHeader(compact);
    if (header) {
      pushCurrent();
      current = {
        key: header[0],
        title: header[1],
        description: header[2],
        lines: [],
      };
      return;
    }
    const parsed = parseAssistantLine(compact);
    if (parsed?.text) current.lines.push(parsed);
  });
  pushCurrent();
  return sections;
}

function buildAssistantSourceSummary(sources) {
  const rows = Array.isArray(sources) ? sources : [];
  const pages = [];
  const pageSeen = new Set();
  const items = [];
  rows.forEach((item) => {
    if (!item || typeof item !== 'object') return;
    const row = {
      type: String(item.type || '').trim(),
      label: String(item.label || '').trim(),
      summary: String(item.summary || '').trim(),
      file_url: String(item.file_url || '').trim(),
    };
    if (row.label || row.summary) items.push(row);
    (Array.isArray(item.pages) ? item.pages : []).forEach((page) => {
      const normalized = typeof page === 'object'
        ? `${String(page.title || '知识文档').trim()}#P${String(page.page || '').trim()}`
        : String(page || '').trim();
      if (!normalized || pageSeen.has(normalized)) return;
      pageSeen.add(normalized);
      pages.push(normalized);
    });
  });
  return {
    pages,
    items: items.slice(0, 8),
  };
}

function buildKnowledgeDocumentUrl(fileUrl, page) {
  const base = String(fileUrl || '').trim();
  const normalizedPage = String(page || '').trim();
  if (!base) return '';
  if (!normalizedPage) return base;
  return `${base}${base.includes('#') ? '&' : '#'}page=${encodeURIComponent(normalizedPage)}`;
}

function getPreferredKnowledgeDocument(sourceSummary) {
  const rows = Array.isArray(sourceSummary?.items) ? sourceSummary.items : [];
  const candidates = rows.filter((item) => String(item?.file_url || '').trim());
  if (!candidates.length) return null;
  const score = (item) => {
    const label = String(item?.label || '').toLowerCase();
    const summary = String(item?.summary || '').toLowerCase();
    let total = 0;
    if (String(item?.type || '').trim() === 'knowledge_document') total += 4;
    if (label.includes('手册') || label.includes('manual')) total += 3;
    if (summary.includes('手册') || summary.includes('manual')) total += 2;
    return total;
  };
  return [...candidates].sort((a, b) => score(b) - score(a))[0] || candidates[0];
}

function normalizePreviewPage(page) {
  const digits = String(page || '').replace(/[^\d]/g, '');
  if (!digits) return '';
  const numeric = Number.parseInt(digits, 10);
  return Number.isFinite(numeric) && numeric > 0 ? String(numeric) : '';
}

function nowTimeLabel() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function createUserMessage(content) {
  return {
    id: `user-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'user',
    content,
    createdAt: nowTimeLabel(),
  };
}

function createPendingMessage(prompt) {
  return {
    id: `pending-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    content: '正在整理上下文、查询数据并组织回答…',
    isPending: true,
    pendingPrompt: prompt,
    createdAt: nowTimeLabel(),
  };
}

function createAssistantMessage(data, fallbackPrompt = '') {
  return {
    id: `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    content: data?.response || 'AI 暂时没有返回内容。',
    meta: buildAssistantMeta(data),
    sections: buildAssistantSections(data?.response),
    sourceSummary: buildAssistantSourceSummary(data?.sources),
    suggestedActions: Array.isArray(data?.suggested_actions) ? data.suggested_actions.slice(0, 6) : [],
    actionCards: Array.isArray(data?.action_cards) ? data.action_cards.slice(0, 3) : [],
    createdAt: nowTimeLabel(),
    prompt: fallbackPrompt,
  };
}

function createErrorMessage(detail, prompt = '') {
  return {
    id: `error-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    content: `请求失败：${detail}`,
    isError: true,
    createdAt: nowTimeLabel(),
    prompt,
  };
}

function sanitizeMessagesForCache(items) {
  return (Array.isArray(items) ? items : []).slice(-20).map((item) => ({
    id: item.id,
    role: item.role,
    content: item.content,
    meta: item.meta || [],
    sections: item.sections || [],
    sourceSummary: item.sourceSummary || { pages: [], items: [] },
    suggestedActions: item.suggestedActions || [],
    actionCards: item.actionCards || [],
    isError: Boolean(item.isError),
    createdAt: item.createdAt || '',
    prompt: item.prompt || '',
  }));
}

function AppBody() {
  const { message } = AntdApp.useApp();
  const [token, setToken] = useState(localStorage.getItem('cs_workspace_token') || '');
  const [userId, setUserId] = useState(localStorage.getItem('cs_workspace_user_id') || 'store-admin');
  const [loginLoading, setLoginLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [text, setText] = useState('');
  const [messages, setMessages] = useState(() => {
    try {
      const raw = localStorage.getItem(CHAT_CACHE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [loginForm] = Form.useForm();
  const messageEndRef = useRef(null);
  const [knowledgePreviewVisible, setKnowledgePreviewVisible] = useState(false);
  const [knowledgePreviewUrl, setKnowledgePreviewUrl] = useState('');
  const [knowledgePreviewTitle, setKnowledgePreviewTitle] = useState('');
  const [knowledgePreviewDocUrl, setKnowledgePreviewDocUrl] = useState('');
  const [knowledgePreviewPage, setKnowledgePreviewPage] = useState('');
  const [knowledgePreviewPageInput, setKnowledgePreviewPageInput] = useState('');
  const [knowledgePreviewRecentPages, setKnowledgePreviewRecentPages] = useState([]);
  const [knowledgePreviewContextPages, setKnowledgePreviewContextPages] = useState([]);
  const [knowledgePreviewContextItems, setKnowledgePreviewContextItems] = useState([]);

  const authHeaders = useMemo(() => {
    if (!token) return {};
    return { Authorization: `Bearer ${token}`, 'X-Store-Id': 'default' };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    localStorage.setItem(CHAT_CACHE_KEY, JSON.stringify(sanitizeMessagesForCache(messages)));
  }, [messages, token]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  useEffect(() => {
    const handleKnowledgePreviewHotkey = (event) => {
      if (!knowledgePreviewVisible || !knowledgePreviewUrl) return;
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        jumpKnowledgePreviewPage(-1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        jumpKnowledgePreviewPage(1);
      }
    };
    window.addEventListener('keydown', handleKnowledgePreviewHotkey);
    return () => window.removeEventListener('keydown', handleKnowledgePreviewHotkey);
  }, [knowledgePreviewVisible, knowledgePreviewUrl, knowledgePreviewPage, knowledgePreviewDocUrl]);

  useEffect(() => {
    if (knowledgePreviewVisible) return;
    setKnowledgePreviewUrl('');
    setKnowledgePreviewTitle('');
    setKnowledgePreviewDocUrl('');
    setKnowledgePreviewPage('');
    setKnowledgePreviewPageInput('');
    setKnowledgePreviewRecentPages([]);
    setKnowledgePreviewContextPages([]);
    setKnowledgePreviewContextItems([]);
  }, [knowledgePreviewVisible]);

  const onLogin = async (values) => {
    setLoginLoading(true);
    setError('');
    try {
      const body = new URLSearchParams();
      body.set('username', values.username);
      body.set('password', values.password);
      const response = await api.post('/auth/token', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      localStorage.setItem('cs_workspace_token', response.data.access_token);
      localStorage.setItem('cs_workspace_user_id', values.username);
      setToken(response.data.access_token);
      setUserId(values.username);
      message.success('登录成功，已进入 AI 对话');
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || '登录失败';
      setError(String(detail));
      message.error(`登录失败: ${detail}`);
    } finally {
      setLoginLoading(false);
    }
  };

  const onLogout = () => {
    localStorage.removeItem('cs_workspace_token');
    localStorage.removeItem('cs_workspace_user_id');
    localStorage.removeItem(CHAT_CACHE_KEY);
    setToken('');
    setMessages([]);
    setText('');
    setError('');
    message.info('已退出登录');
  };

  const sendMessage = async (overrideText = '') => {
    const content = String(overrideText || text).trim();
    if (!content || sending) return;

    const userMessage = createUserMessage(content);
    const pendingMessage = createPendingMessage(content);

    setSending(true);
    setError('');
    setMessages((prev) => [...prev, userMessage, pendingMessage]);
    if (!overrideText) setText('');

    try {
      const response = await api.post(
        '/ai/assistant/chat',
        {
          user_id: userId,
          message: content,
          context: {},
        },
        { headers: authHeaders, timeout: 45000 },
      );
      const assistantMessage = createAssistantMessage(response?.data, content);
      setMessages((prev) =>
        prev.map((item) => (item.id === pendingMessage.id ? assistantMessage : item)),
      );
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || '请求失败';
      setError(String(detail));
      setMessages((prev) =>
        prev.map((item) => (item.id === pendingMessage.id ? createErrorMessage(detail, content) : item)),
      );
    } finally {
      setSending(false);
    }
  };

  const pushKnowledgePreviewHistory = (page) => {
    const normalized = normalizePreviewPage(page);
    if (!normalized) return;
    setKnowledgePreviewRecentPages((prev) => [normalized, ...prev.filter((item) => item !== normalized)].slice(0, 8));
  };

  const updateKnowledgePreviewUrl = (docUrl, page = '') => {
    const base = String(docUrl || '').trim().split('#')[0];
    if (!base) return;
    const normalized = normalizePreviewPage(page);
    setKnowledgePreviewPage(normalized);
    setKnowledgePreviewPageInput(normalized);
    setKnowledgePreviewUrl(buildKnowledgeDocumentUrl(base, normalized));
    pushKnowledgePreviewHistory(normalized);
  };

  const openKnowledgePreview = (fileUrl, page = '', title = '', sourceSummary = null) => {
    const base = String(fileUrl || '').trim().split('#')[0];
    if (!base) {
      message.warning('这个来源当前没有可直接打开的资料链接');
      return;
    }
    setKnowledgePreviewDocUrl(base);
    setKnowledgePreviewTitle(String(title || '').trim() || '标准资料预览');
    setKnowledgePreviewContextPages(Array.isArray(sourceSummary?.pages) ? sourceSummary.pages.slice(0, 8) : []);
    setKnowledgePreviewContextItems(Array.isArray(sourceSummary?.items) ? sourceSummary.items.slice(0, 6) : []);
    updateKnowledgePreviewUrl(base, page);
    setKnowledgePreviewVisible(true);
  };

  const jumpKnowledgePreviewPage = (delta = 0) => {
    if (!knowledgePreviewDocUrl) return;
    const current = Number.parseInt(knowledgePreviewPage || '1', 10) || 1;
    const next = Math.max(1, current + delta);
    updateKnowledgePreviewUrl(knowledgePreviewDocUrl, String(next));
  };

  const goToKnowledgePreviewPage = () => {
    if (!knowledgePreviewDocUrl) return;
    const normalized = normalizePreviewPage(knowledgePreviewPageInput);
    if (!normalized) {
      message.warning('请输入有效页码');
      return;
    }
    updateKnowledgePreviewUrl(knowledgePreviewDocUrl, normalized);
  };

  const copyKnowledgePreviewLink = async () => {
    if (!knowledgePreviewUrl) {
      message.warning('当前没有可复制的资料链接');
      return;
    }
    try {
      await navigator.clipboard.writeText(knowledgePreviewUrl);
      message.success('已复制当前页链接');
    } catch {
      message.warning('复制失败，请手动复制地址');
    }
  };

  const openAssistantSourceItem = (item, sourceSummary, page = '') => {
    const fileUrl = String(item?.file_url || '').trim();
    if (fileUrl) {
      openKnowledgePreview(fileUrl, page, item?.label || '参考资料', sourceSummary);
      return;
    }
    const preferredDoc = getPreferredKnowledgeDocument(sourceSummary);
    if (preferredDoc?.file_url) {
      const targetPage = String(page || sourceSummary?.pages?.[0] || '').trim();
      openKnowledgePreview(preferredDoc.file_url, targetPage, preferredDoc.label || '标准资料', sourceSummary);
      return;
    }
    const firstPage = String(page || sourceSummary?.pages?.[0] || '').trim();
    if (firstPage) {
      message.info(`当前来源没有直接链接，请优先查看第 ${firstPage} 页。`);
      return;
    }
    message.warning('这个来源当前没有可直接打开的资料链接。');
  };

  const clearMessages = () => {
    localStorage.removeItem(CHAT_CACHE_KEY);
    setMessages([]);
    setError('');
    message.success('已清空当前会话');
  };

  const copyText = async (content, successText = '已复制') => {
    if (!String(content || '').trim()) return;
    try {
      await navigator.clipboard.writeText(String(content));
      message.success(successText);
    } catch {
      message.warning('复制失败，请手动复制');
    }
  };

  if (!token) {
    return (
      <Layout className="chat-shell">
        <Content className="login-wrap">
          <Card className="login-card" title="AI 门店助理登录">
            <Form
              form={loginForm}
              layout="vertical"
              initialValues={{ username: 'admin', password: 'change_me_now' }}
              onFinish={onLogin}
            >
              <Form.Item label="用户名" name="username" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item label="密码" name="password" rules={[{ required: true }]}>
                <Input.Password />
              </Form.Item>
              <Button type="primary" htmlType="submit" block loading={loginLoading}>
                登录
              </Button>
            </Form>
            {error ? <Alert style={{ marginTop: 12 }} type="error" message={error} showIcon /> : null}
          </Card>
        </Content>
      </Layout>
    );
  }

  return (
    <Layout className="chat-shell">
      <Header className="chat-header">
        <div>
          <Title level={4} className="chat-title">
            AI 门店助理
          </Title>
          <Text type="secondary">查系统、写入、维修建议、门店运营提醒，都在一个对话框里完成。</Text>
        </div>
        <Space>
          <Tag color="green">在线</Tag>
          <Button onClick={onLogout}>退出</Button>
        </Space>
      </Header>
      <Content className="chat-content">
        {error ? <Alert className="chat-alert" type="error" message={error} showIcon /> : null}
        <Card className="chat-card">
          <div className="chat-toolbar">
            <div className="chat-toolbar-copy">
              <strong>快捷提问</strong>
              <span>点一下就能发，适合快速验证系统是否命中正确数据。</span>
            </div>
            <div className="chat-toolbar-actions">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="chat-quick-chip"
                  onClick={() => sendMessage(prompt)}
                  disabled={sending}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="chat-empty">
                <strong>直接问就行，不用切页面。</strong>
                <span>例如查工单、查客户、查车型、问维修方法，或者直接让 AI 新建客户、补备注、生成报价草稿。</span>
              </div>
            ) : null}

            {messages.map((item) => (
              <div
                key={item.id}
                className={`chat-row ${item.role === 'user' ? 'chat-row-user' : 'chat-row-assistant'}`}
              >
                <div
                  className={`chat-bubble ${item.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'} ${item.isError ? 'chat-bubble-error' : ''} ${item.isPending ? 'chat-bubble-pending' : ''}`}
                >
                  <div className="chat-bubble-head">
                    <strong>{item.role === 'user' ? '你' : 'AI 门店助理'}</strong>
                    <span>{item.createdAt}</span>
                  </div>
                  <div className="chat-bubble-copy">{item.content}</div>

                  {item.role === 'assistant' && item.sections?.length ? (
                    <div className="chat-structured">
                      {item.sections.map((section) => (
                        <div key={section.key} className="chat-structured-card">
                          <div className="chat-structured-head">
                            <strong>{section.title}</strong>
                            <span>{section.description}</span>
                          </div>
                          <div className="chat-structured-list">
                            {section.lines.map((line, lineIndex) => (
                              <div key={`${section.key}-${lineIndex}`} className="chat-structured-line">
                                <span className="chat-structured-index">{lineIndex + 1}</span>
                                <div className="chat-structured-copy">
                                  <span>{line.text}</span>
                                  {line.tag ? (
                                    <span className={`chat-source-chip chat-source-chip-${sourceTagTone(line.tag)}`}>
                                      {line.tag}
                                    </span>
                                  ) : null}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  {item.role === 'assistant' && item.actionCards?.length ? (
                    <div className="chat-action-panel">
                      <div className="chat-source-head">
                        <strong>建议直接执行</strong>
                        <span>这是 AI 当前认为最顺手的下一步。</span>
                      </div>
                      <div className="chat-action-list">
                        {item.actionCards.map((card, index) => (
                          <div key={`${card.action || 'card'}-${index}`} className="chat-action-card">
                            <div>
                              <strong>{card.label || '建议动作'}</strong>
                              <p>{card.description || card.action || '可直接执行的下一步'}</p>
                            </div>
                            <span className="chat-meta-chip chat-meta-chip-info">{card.action || 'action'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {item.role === 'assistant' && (item.sourceSummary?.pages?.length || item.sourceSummary?.items?.length) ? (
                    <div className="chat-source-panel">
                      <div className="chat-source-head">
                        <strong>参考来源</strong>
                        {item.sourceSummary?.pages?.length ? <span>重点页码：{item.sourceSummary.pages.join('、')}</span> : null}
                      </div>
                      {item.sourceSummary?.pages?.length ? (
                        <div className="chat-source-pages">
                          {item.sourceSummary.pages.map((page) => (
                            <Button
                              key={`page-${page}`}
                              className="chat-source-page-button"
                              type="default"
                              size="small"
                              onClick={() => openAssistantSourceItem({}, item.sourceSummary, page)}
                            >
                              页码 {page}
                            </Button>
                          ))}
                        </div>
                      ) : null}
                      {item.sourceSummary?.items?.length ? (
                        <div className="chat-source-items">
                          {item.sourceSummary.items.map((sourceItem, sourceIndex) => (
                            <div key={`${sourceItem.type || 'source'}-${sourceIndex}`} className="chat-source-item">
                              <div>
                                <div className="chat-source-item-title">
                                  <strong>{sourceItem.label || sourceItem.summary || '参考记录'}</strong>
                                  <span className="chat-source-item-type">{sourceTypeLabel(sourceItem.type)}</span>
                                </div>
                                <p>{sourceItem.summary || sourceTypeLabel(sourceItem.type)}</p>
                              </div>
                              {(sourceItem.file_url || sourceItem.type === 'knowledge') ? (
                                <Button
                                  type="link"
                                  size="small"
                                  onClick={() => openAssistantSourceItem(sourceItem, item.sourceSummary)}
                                >
                                  打开
                                </Button>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  {item.role === 'assistant' && item.suggestedActions?.length ? (
                    <div className="chat-follow-ups">
                      {item.suggestedActions.map((action, index) => (
                        <button
                          key={`${action}-${index}`}
                          type="button"
                          className="chat-follow-chip"
                          onClick={() => sendMessage(action)}
                          disabled={sending}
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                  ) : null}

                  {item.role === 'assistant' && item.meta?.length ? (
                    <div className="chat-meta">
                      {item.meta.map((metaItem, metaIndex) => (
                        <span
                          key={`${metaItem.label}-${metaIndex}`}
                          className={`chat-meta-chip chat-meta-chip-${metaItem.tone || 'muted'}`}
                        >
                          {metaItem.label}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  <div className="chat-row-actions">
                    {item.role === 'assistant' && !item.isPending ? (
                      <Button type="link" size="small" onClick={() => copyText(item.content, '回答已复制')}>
                        复制回答
                      </Button>
                    ) : null}
                    {item.role === 'assistant' && item.prompt ? (
                      <Button type="link" size="small" onClick={() => sendMessage(item.prompt)} disabled={sending}>
                        重试这条
                      </Button>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messageEndRef} />
          </div>

          <div className="chat-input-wrap">
            <Input.TextArea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="输入你的问题或动作，Enter 发送，Shift+Enter 换行"
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
            />
            <div className="chat-input-hint">支持直接发自然语言动作，例如“给这个工单加备注 ……”、“新建客户 ……”。</div>
            <div className="chat-actions">
              <Button onClick={clearMessages}>清空会话</Button>
              <Button type="primary" onClick={() => sendMessage()} loading={sending}>
                发送
              </Button>
            </div>
          </div>
        </Card>
        <Modal
          open={knowledgePreviewVisible}
          title={knowledgePreviewTitle || '标准资料预览'}
          width="88vw"
          className="knowledge-preview-modal"
          onCancel={() => setKnowledgePreviewVisible(false)}
          footer={
            <div className="knowledge-preview-footer">
              <div className="knowledge-preview-toolbar">
                <div className="knowledge-preview-toolbar-main">
                  <span className="knowledge-preview-label">资料：{knowledgePreviewTitle || '标准资料预览'}</span>
                  <span className="knowledge-preview-label">当前页：{knowledgePreviewPage || '-'}</span>
                  <Input
                    value={knowledgePreviewPageInput}
                    onChange={(event) => setKnowledgePreviewPageInput(event.target.value)}
                    className="knowledge-preview-page-input"
                    placeholder="输入页码"
                    onPressEnter={goToKnowledgePreviewPage}
                  />
                  <Button size="small" onClick={goToKnowledgePreviewPage} disabled={!knowledgePreviewUrl}>
                    跳转
                  </Button>
                  <Button size="small" onClick={() => jumpKnowledgePreviewPage(-1)} disabled={!knowledgePreviewUrl}>
                    上一页
                  </Button>
                  <Button size="small" onClick={() => jumpKnowledgePreviewPage(1)} disabled={!knowledgePreviewUrl}>
                    下一页
                  </Button>
                  <Button size="small" onClick={copyKnowledgePreviewLink} disabled={!knowledgePreviewUrl}>
                    复制当前页链接
                  </Button>
                </div>
                <div className="knowledge-preview-toolbar-side">
                  <span className="knowledge-preview-hint">左右方向键可翻页</span>
                  <Button
                    size="small"
                    onClick={() => knowledgePreviewUrl && window.open(knowledgePreviewUrl, '_blank')}
                    disabled={!knowledgePreviewUrl}
                  >
                    新窗口打开
                  </Button>
                  <Button type="primary" size="small" onClick={() => setKnowledgePreviewVisible(false)}>
                    关闭
                  </Button>
                </div>
              </div>
              {knowledgePreviewRecentPages.length ? (
                <div className="knowledge-preview-history">
                  <span>最近页码：</span>
                  {knowledgePreviewRecentPages.map((page) => (
                    <Button
                      key={`history-${page}`}
                      type="link"
                      size="small"
                      onClick={() => updateKnowledgePreviewUrl(knowledgePreviewDocUrl, page)}
                    >
                      {page}
                    </Button>
                  ))}
                </div>
              ) : null}
              {knowledgePreviewContextPages.length ? (
                <div className="knowledge-preview-history">
                  <span>本次引用页：</span>
                  {knowledgePreviewContextPages.map((page) => (
                    <Button
                      key={`context-page-${page}`}
                      type={page === knowledgePreviewPage ? 'primary' : 'link'}
                      size="small"
                      onClick={() => updateKnowledgePreviewUrl(knowledgePreviewDocUrl, page)}
                    >
                      {page}
                    </Button>
                  ))}
                </div>
              ) : null}
            </div>
          }
        >
          <div className="knowledge-preview-shell">
            {knowledgePreviewUrl ? (
              <iframe
                title={knowledgePreviewTitle || '标准资料预览'}
                src={knowledgePreviewUrl}
                className="knowledge-preview-frame"
              />
            ) : (
              <div className="knowledge-preview-empty">当前没有可预览的资料地址。</div>
            )}
          </div>
          {knowledgePreviewContextItems.length ? (
            <div className="knowledge-preview-context">
              <div className="knowledge-preview-context-head">
                <strong>本次回答引用来源</strong>
                <span>不用回到聊天区也能快速核对</span>
              </div>
              <div className="knowledge-preview-context-list">
                {knowledgePreviewContextItems.map((item, index) => (
                  <div key={`${item.type || 'context'}-${index}`} className="knowledge-preview-context-item">
                    <strong>{item.label || item.summary || '参考记录'}</strong>
                    <p>{item.summary || sourceTypeLabel(item.type)}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </Modal>
      </Content>
    </Layout>
  );
}

export default function App() {
  return (
    <AntdApp>
      <AppBody />
    </AntdApp>
  );
}
