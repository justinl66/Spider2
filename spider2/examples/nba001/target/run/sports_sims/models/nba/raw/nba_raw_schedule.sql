
  
    
    

    create  table
      "nba"."main"."nba_raw_schedule__dbt_tmp"
  
    as (
      select
    id,
    type,
    strptime("Year" || "Date", '%Y %b %-d')::date as "date",
    "Start (ET)",
    "Visitor/Neutral" as "VisTm",
    "Home/Neutral" as "HomeTm",
    "Attend.",
    arena,
    notes,
    series_id
from 'data/nba/nba_schedule.csv'
    );
  
  