view: events {
  sql_table_name: `bigquery-public-data.thelook_ecommerce.events` ;;

  dimension: id {
    primary_key: yes
    type: number
  }

  dimension: user_id {
    type: number
    sql: ${TABLE}.user_id ;;
  }

  dimension: sequence_number {
    type: number
    sql: ${TABLE}.sequence_number ;;
  }

  dimension: session_id {
    type: string
    sql: ${TABLE}.session_id ;;
  }

  dimension_group: created_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.created_at ;;
  }

  dimension: ip_address {
    type: string
    sql: ${TABLE}.ip_address ;;
  }

  dimension: city {
    type: string
    sql: ${TABLE}.city ;;
  }

  dimension: state {
    type: string
    sql: ${TABLE}.state ;;
  }

  dimension: postal_code {
    type: string
    sql: ${TABLE}.postal_code ;;
  }

  dimension: browser {
    type: string
    sql: ${TABLE}.browser ;;
  }

  dimension: traffic_source {
    type: string
    sql: ${TABLE}.traffic_source ;;
  }

  dimension: uri {
    type: string
    sql: ${TABLE}.uri ;;
  }

  dimension: event_type {
    type: string
    sql: ${TABLE}.event_type ;;
  }

  measure: count {
    type: count
  }

  measure: count_distinct_id {
    type: count_distinct
    sql: ${id} ;;
  }

  measure: sum_sequence_number {
    type: sum
    sql: ${sequence_number} ;;
  }

  measure: avg_sequence_number {
    type: average
    sql: ${sequence_number} ;;
  }
}