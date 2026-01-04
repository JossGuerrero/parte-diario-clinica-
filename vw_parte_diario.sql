-- Vista para parte diario consolidado
CREATE OR REPLACE VIEW vw_parte_diario AS
SELECT
  a.fecha_atencion,
  COALESCE(NULLIF(TRIM(m.nombre), ''), 'SIN ASIGNAR') AS medico,
  COALESCE(NULLIF(TRIM(m.especialidad), ''), 'SIN ASIGNAR') AS especialidad,
  COUNT(*) AS total_atenciones,
  SUM(GREATEST(a.valor_consulta, 0)) AS total_consultas,
  SUM(GREATEST(a.valor_medicina, 0)) AS total_medicina
FROM atencion a
LEFT JOIN medico m ON a.medico_id = m.id
WHERE a.fecha_atencion IS NOT NULL
GROUP BY a.fecha_atencion, m.nombre, m.especialidad;
