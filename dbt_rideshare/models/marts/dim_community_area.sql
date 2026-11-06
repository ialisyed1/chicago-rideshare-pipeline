-- The 77 Chicago community areas, plus key 0 for trips outside Chicago or suppressed for privacy.
select area_id, area_name from {{ ref('community_areas') }}
union all
select 0 as area_id, 'Outside Chicago / suppressed' as area_name
