-- Silver: PLACEHOLDER pass-through.
-- JHU_COVID_19's exact schema isn't confirmed against the live account
-- yet (see sql/03_eda_structure.sql block 0 -- DESCRIBE TABLE + sample
-- rows). Once confirmed, replace this with an explicit column list and
-- renaming like the other staging models, following the same pattern.

select * from {{ source('marketplace', 'jhu_covid_19') }}
