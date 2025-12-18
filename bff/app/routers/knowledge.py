from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..core.db import get_db
from ..models import Vehicle, Procedure, ProcedureStep

router = APIRouter(prefix="/mp/knowledge", tags=["Knowledge Base"])

class VehicleSchema(BaseModel):
    key: str
    make: str
    model: str
    year_from: int
    
class StepSchema(BaseModel):
    step_order: int
    instruction: str
    required_tools: Optional[str]
    torque_spec: Optional[str]

class ProcedureSchema(BaseModel):
    id: int
    name: str
    steps: List[StepSchema]

@router.get("/vehicles", response_model=List[VehicleSchema])
async def list_vehicles(make: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Vehicle)
    if make:
        query = query.filter(Vehicle.make == make)
    return query.all()

@router.get("/procedures", response_model=List[dict])
async def get_procedures(vehicle_model_id: int, db: Session = Depends(get_db)):
    """Fetch procedures from Odoo for a specific vehicle model."""
    try:
        # Search drmoto.procedure where vehicle_id = vehicle_model_id
        domain = [['vehicle_id', '=', vehicle_model_id]]
        fields = ['id', 'name', 'description', 'total_cost']
        procedures = odoo_client.execute_kw('drmoto.procedure', 'search_read', [domain], {'fields': fields})
        return procedures
    except Exception as e:
        logger.error(f"Procedure fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch procedures from Odoo")

@router.post("/seed")
async def seed_knowledge(db: Session = Depends(get_db)):
    """
    Seeds the database with a Comprehensive Framework of International and Domestic Motorcycles (2015-2025).
    """
    motorcycles = [
        # ==================== KAWASAKI (川崎) ====================
        {"key": "KAWASAKI|NINJA400|2018|399", "make": "Kawasaki", "model": "Ninja 400", "year_from": 2018, "engine_code": "399cc Twin"},
        {"key": "KAWASAKI|NINJA250|2018|249", "make": "Kawasaki", "model": "Ninja 250", "year_from": 2018, "engine_code": "249cc Twin"},
        {"key": "KAWASAKI|NINJA500|2024|451", "make": "Kawasaki", "model": "Ninja 500", "year_from": 2024, "engine_code": "451cc Twin"},
        {"key": "KAWASAKI|NINJA650|2017|649", "make": "Kawasaki", "model": "Ninja 650", "year_from": 2017, "engine_code": "649cc Twin"},
        {"key": "KAWASAKI|ZX6R|2019|636", "make": "Kawasaki", "model": "Ninja ZX-6R", "year_from": 2019, "engine_code": "636cc Inline-4"},
        {"key": "KAWASAKI|ZX10R|2021|998", "make": "Kawasaki", "model": "Ninja ZX-10R", "year_from": 2021, "engine_code": "998cc Inline-4"},
        {"key": "KAWASAKI|Z400|2019|399", "make": "Kawasaki", "model": "Z400", "year_from": 2019, "engine_code": "399cc Twin"},
        {"key": "KAWASAKI|Z650|2017|649", "make": "Kawasaki", "model": "Z650", "year_from": 2017, "engine_code": "649cc Twin"},
        {"key": "KAWASAKI|Z900|2017|948", "make": "Kawasaki", "model": "Z900", "year_from": 2017, "engine_code": "948cc Inline-4"},
        {"key": "KAWASAKI|Z900RS|2018|948", "make": "Kawasaki", "model": "Z900RS", "year_from": 2018, "engine_code": "948cc Inline-4"},
        {"key": "KAWASAKI|VERSYS650|2015|649", "make": "Kawasaki", "model": "Versys 650", "year_from": 2015, "engine_code": "649cc Twin"},
        {"key": "KAWASAKI|VULCANS|2015|649", "make": "Kawasaki", "model": "Vulcan S", "year_from": 2015, "engine_code": "649cc Twin"},

        # ==================== HONDA (本田) ====================
        {"key": "HONDA|CBR650R|2019|649", "make": "Honda", "model": "CBR650R", "year_from": 2019, "engine_code": "649cc Inline-4"},
        {"key": "HONDA|CB650R|2019|649", "make": "Honda", "model": "CB650R", "year_from": 2019, "engine_code": "649cc Inline-4"},
        {"key": "HONDA|CBR500R|2019|471", "make": "Honda", "model": "CBR500R", "year_from": 2019, "engine_code": "471cc Twin"},
        {"key": "HONDA|CB500F|2019|471", "make": "Honda", "model": "CB500F", "year_from": 2019, "engine_code": "471cc Twin"},
        {"key": "HONDA|CB500X|2019|471", "make": "Honda", "model": "CB500X", "year_from": 2019, "engine_code": "471cc Twin"},
        {"key": "HONDA|CM300|2020|286", "make": "Honda", "model": "CM300 (Rebel 300)", "year_from": 2020, "engine_code": "286cc Single"},
        {"key": "HONDA|CM500|2017|471", "make": "Honda", "model": "CM500 (Rebel 500)", "year_from": 2017, "engine_code": "471cc Twin"},
        {"key": "HONDA|CM1100|2021|1084", "make": "Honda", "model": "CM1100 (Rebel 1100)", "year_from": 2021, "engine_code": "1084cc Twin"},
        {"key": "HONDA|CBR1000RR|2020|1000", "make": "Honda", "model": "CBR1000RR-R", "year_from": 2020, "engine_code": "1000cc Inline-4"},
        {"key": "HONDA|CRF1100L|2020|1084", "make": "Honda", "model": "Africa Twin CRF1100L", "year_from": 2020, "engine_code": "1084cc Twin"},
        {"key": "HONDA|GL1800|2018|1833", "make": "Honda", "model": "Gold Wing GL1800", "year_from": 2018, "engine_code": "1833cc Flat-6"},
        {"key": "HONDA|XADV750|2021|745", "make": "Honda", "model": "X-ADV 750", "year_from": 2021, "engine_code": "745cc Twin"},

        # ==================== YAMAHA (雅马哈) ====================
        {"key": "YAMAHA|R3|2019|321", "make": "Yamaha", "model": "YZF-R3", "year_from": 2019, "engine_code": "321cc Twin"},
        {"key": "YAMAHA|R7|2021|689", "make": "Yamaha", "model": "YZF-R7", "year_from": 2021, "engine_code": "689cc Twin"},
        {"key": "YAMAHA|R1|2020|998", "make": "Yamaha", "model": "YZF-R1", "year_from": 2020, "engine_code": "998cc Inline-4"},
        {"key": "YAMAHA|MT03|2020|321", "make": "Yamaha", "model": "MT-03", "year_from": 2020, "engine_code": "321cc Twin"},
        {"key": "YAMAHA|MT07|2021|689", "make": "Yamaha", "model": "MT-07", "year_from": 2021, "engine_code": "689cc Twin"},
        {"key": "YAMAHA|MT09|2021|890", "make": "Yamaha", "model": "MT-09", "year_from": 2021, "engine_code": "890cc Triple"},
        {"key": "YAMAHA|XMAX300|2018|292", "make": "Yamaha", "model": "XMAX 300", "year_from": 2018, "engine_code": "292cc Single"},
        {"key": "YAMAHA|TMAX560|2020|562", "make": "Yamaha", "model": "TMAX 560", "year_from": 2020, "engine_code": "562cc Twin"},

        # ==================== BMW (宝马) ====================
        {"key": "BMW|S1000RR|2019|999", "make": "BMW", "model": "S1000RR", "year_from": 2019, "engine_code": "999cc Inline-4"},
        {"key": "BMW|R1250GS|2019|1254", "make": "BMW", "model": "R1250GS", "year_from": 2019, "engine_code": "1254cc Boxer"},
        {"key": "BMW|R1300GS|2024|1300", "make": "BMW", "model": "R1300GS", "year_from": 2024, "engine_code": "1300cc Boxer"},
        {"key": "BMW|F900R|2020|895", "make": "BMW", "model": "F900R", "year_from": 2020, "engine_code": "895cc Twin"},
        {"key": "BMW|G310R|2016|313", "make": "BMW", "model": "G310R", "year_from": 2016, "engine_code": "313cc Single"},
        {"key": "BMW|G310GS|2017|313", "make": "BMW", "model": "G310GS", "year_from": 2017, "engine_code": "313cc Single"},

        # ==================== DUCATI (杜卡迪) ====================
        {"key": "DUCATI|V4S|2020|1103", "make": "Ducati", "model": "Panigale V4 S", "year_from": 2020, "engine_code": "1103cc V4"},
        {"key": "DUCATI|V2|2020|955", "make": "Ducati", "model": "Panigale V2", "year_from": 2020, "engine_code": "955cc V2"},
        {"key": "DUCATI|SFV4|2020|1103", "make": "Ducati", "model": "Streetfighter V4", "year_from": 2020, "engine_code": "1103cc V4"},
        {"key": "DUCATI|MONSTER937|2021|937", "make": "Ducati", "model": "Monster 937", "year_from": 2021, "engine_code": "937cc V2"},
        {"key": "DUCATI|SCRAMBLER800|2015|803", "make": "Ducati", "model": "Scrambler 800", "year_from": 2015, "engine_code": "803cc V2"},

        # ==================== CFMOTO (春风) ====================
        {"key": "CFMOTO|250SR|2019|249", "make": "CFMOTO", "model": "250SR", "year_from": 2019, "engine_code": "249cc Single"},
        {"key": "CFMOTO|450SR|2022|450", "make": "CFMOTO", "model": "450SR", "year_from": 2022, "engine_code": "450cc 270°-Crank"},
        {"key": "CFMOTO|675SR|2024|675", "make": "CFMOTO", "model": "675SR-R", "year_from": 2024, "engine_code": "675cc Triple"},
        {"key": "CFMOTO|450NK|2023|450", "make": "CFMOTO", "model": "450NK", "year_from": 2023, "engine_code": "450cc Twin"},
        {"key": "CFMOTO|800NK|2023|799", "make": "CFMOTO", "model": "800NK", "year_from": 2023, "engine_code": "799cc Twin"},
        {"key": "CFMOTO|800MT|2021|799", "make": "CFMOTO", "model": "800MT", "year_from": 2021, "engine_code": "799cc Twin"},
        {"key": "CFMOTO|700CLX|2020|693", "make": "CFMOTO", "model": "700CL-X", "year_from": 2020, "engine_code": "693cc Twin"},

        # ==================== QJMOTOR (钱江) ====================
        {"key": "QJMOTOR|SRK600|2020|600", "make": "QJMOTOR", "model": "SRK 600 (赛600)", "year_from": 2020, "engine_code": "600cc Inline-4"},
        {"key": "QJMOTOR|SRK400|2022|400", "make": "QJMOTOR", "model": "SRK 400 (赛400)", "year_from": 2022, "engine_code": "400cc Twin"},
        {"key": "QJMOTOR|SRK800|2024|778", "make": "QJMOTOR", "model": "SRK 800RR (赛800)", "year_from": 2024, "engine_code": "778cc Inline-4"},
        {"key": "QJMOTOR|FLASH300|2021|300", "make": "QJMOTOR", "model": "Flash 300S (闪300)", "year_from": 2021, "engine_code": "300cc V2"},
        {"key": "QJMOTOR|SRT800|2021|754", "make": "QJMOTOR", "model": "SRT 800 (骁800)", "year_from": 2021, "engine_code": "754cc Twin"},

        # ==================== KOVE (凯越) ====================
        {"key": "KOVE|321RR|2021|321", "make": "KOVE", "model": "321RR", "year_from": 2021, "engine_code": "321cc Twin"},
        {"key": "KOVE|450RR|2023|443", "make": "KOVE", "model": "450RR", "year_from": 2023, "engine_code": "443cc Inline-4"},
        {"key": "KOVE|800X|2023|799", "make": "KOVE", "model": "800X Super Adventure", "year_from": 2023, "engine_code": "799cc Twin"},

        # ==================== VOGE (无极) ====================
        {"key": "VOGE|525RR|2023|494", "make": "VOGE", "model": "525RR", "year_from": 2023, "engine_code": "494cc Twin"},
        {"key": "VOGE|300RR|2019|292", "make": "VOGE", "model": "300RR", "year_from": 2019, "engine_code": "292cc Single"},
        {"key": "VOGE|525DSX|2023|494", "make": "VOGE", "model": "525DSX", "year_from": 2023, "engine_code": "494cc Twin"},
        {"key": "VOGE|CU525|2023|494", "make": "VOGE", "model": "CU525", "year_from": 2023, "engine_code": "494cc Twin"},
    ]

    for m in motorcycles:
        if not db.query(Vehicle).filter_by(key=m["key"]).first():
            db.add(Vehicle(**m))
    
    db.commit()
    
    # 2. Add a Sample Procedure for Ninja 400 (Most popular)
    v_key = "KAWASAKI|NINJA400|2018|399"
    p_name = "Oil Change (Ninja 400)"
    
    # Check if exists
    if not db.query(Procedure).filter_by(vehicle_key=v_key, name=p_name).first():
        proc = Procedure(vehicle_key=v_key, name=p_name, description="Standard oil and filter change for Ninja 400.")
        db.add(proc)
        db.commit()
        
        steps = [
            {"order": 1, "text": "Place bike on rear stand. Warm up engine for 2 mins.", "tools": "['rear_stand']", "torque": None},
            {"order": 2, "text": "Remove lower fairing (4mm hex).", "tools": "['hex_4mm']", "torque": None},
            {"order": 3, "text": "Remove drain bolt (17mm). Drain oil.", "tools": "['wrench_17mm', 'oil_pan']", "torque": None},
            {"order": 4, "text": "Remove oil filter.", "tools": "['filter_wrench']", "torque": None},
            {"order": 5, "text": "Install new filter. Hand tighten.", "tools": "['hand']", "torque": "{'val': 17, 'unit': 'Nm'}"},
            {"order": 6, "text": "Install drain bolt with new crush washer.", "tools": "['torque_wrench']", "torque": "{'val': 30, 'unit': 'Nm'}"},
            {"order": 7, "text": "Fill 2.0L of 10W-40 Synthetic Oil.", "tools": "['funnel']", "torque": None},
        ]
        
        for s in steps:
            db.add(ProcedureStep(
                procedure_id=proc.id,
                step_order=s['order'],
                instruction=s['text'],
                required_tools=s['tools'],
                torque_spec=s['torque']
            ))
        db.commit()
        
    return {"status": "seeded", "count": len(motorcycles)}
