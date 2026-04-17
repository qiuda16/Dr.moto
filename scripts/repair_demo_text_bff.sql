UPDATE work_orders
SET vehicle_plate = '沪BA01',
    description = '常规保养，检查刹车片（演示数据）'
WHERE uuid = '83b28f3e-8132-46e6-a9b6-75aef5474157';

UPDATE work_orders
SET description = '前制动偏软，顺便做常规检查'
WHERE uuid = '3cebd998-dd7f-42b3-b1fc-3abf86d4280b';

UPDATE work_orders
SET description = '客户上传图片，待补完整主诉'
WHERE uuid = 'a1d287e4-dcd9-4716-8d4b-f0e0297f133a';

UPDATE work_order_process_records
SET symptom_draft = '前制动偏软，需要检查刹车油和制动手感',
    symptom_confirmed = '确认前制动手感偏软，建议检查刹车油并排空气',
    quick_check_json = jsonb_set(COALESCE(quick_check_json::jsonb, '{}'::jsonb), '{brake}', '"前制动手感偏软"')::json
WHERE work_order_uuid = '3cebd998-dd7f-42b3-b1fc-3abf86d4280b';

UPDATE work_order_process_records
SET symptom_draft = '客户上传图片，待补完整描述',
    symptom_confirmed = '待门店进一步确认故障现象'
WHERE work_order_uuid = 'a1d287e4-dcd9-4716-8d4b-f0e0297f133a';

UPDATE vehicle_health_records
SET notes = '演示体检记录，建议复查前制动系统',
    extra_json = '{"brake":"建议复查前制动系统","chain":"正常"}'::jsonb
WHERE customer_id = '184' AND vehicle_plate = 'TEST1234';

UPDATE quotes
SET items_json = '[
  {"item_type":"part","code":"P-001","name":"刹车油 DOT4","qty":1.0,"unit_price":68.0},
  {"item_type":"service","code":"S-001","name":"前制动系统检查","qty":1.0,"unit_price":180.0}
]'::jsonb
WHERE work_order_uuid = '3cebd998-dd7f-42b3-b1fc-3abf86d4280b';
