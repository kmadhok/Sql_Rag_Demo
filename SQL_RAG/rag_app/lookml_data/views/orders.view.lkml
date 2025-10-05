view: orders {
  sql_table_name: `bigquery-public-data.thelook_ecommerce.orders` ;;

  dimension: order_id {
    primary_key: yes
    type: number
  }

  dimension: user_id {
    type: number
    sql: ${TABLE}.user_id ;;
  }

  dimension: status {
    type: string
    sql: ${TABLE}.status ;;
  }

  dimension: gender {
    type: string
    sql: ${TABLE}.gender ;;
  }

  dimension_group: created_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.created_at ;;
  }

  dimension_group: returned_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.returned_at ;;
  }

  dimension_group: shipped_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.shipped_at ;;
  }

  dimension_group: delivered_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.delivered_at ;;
  }

  dimension: num_of_item {
    type: number
    sql: ${TABLE}.num_of_item ;;
  }

  measure: count {
    type: count
  }

  measure: count_distinct_order_id {
    type: count_distinct
    sql: ${order_id} ;;
  }

  measure: sum_num_of_item {
    type: sum
    sql: ${num_of_item} ;;
  }

  measure: avg_num_of_item {
    type: average
    sql: ${num_of_item} ;;
  }
}