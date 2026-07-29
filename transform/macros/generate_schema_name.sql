{#
  dbt's default behaviour concatenates the target schema with any custom
  +schema config (e.g. "gold_marts"). We want the Medallion layer name
  used exactly as configured in dbt_project.yml (SILVER, GOLD) so the
  schemas line up 1:1 with what was created in sql/00_setup_warehouse_and_db.sql.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
