view: inventory_items {
  sql_table_name: `bigquery-public-data.thelook_ecommerce.inventory_items` ;;

  dimension: id {
    primary_key: yes
    type: number
  }

  dimension: product_id {
    type: number
    sql: ${TABLE}.product_id ;;
  }

  dimension_group: created_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.created_at ;;
  }

  dimension_group: sold_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.sold_at ;;
  }

  dimension: cost {
    type: number
    sql: ${TABLE}.cost ;;
  }

  dimension: product_category {
    type: string
    sql: ${TABLE}.product_category ;;
  }

  dimension: product_name {
    type: string
    sql: ${TABLE}.product_name ;;
  }

  dimension: product_brand {
    type: string
    sql: ${TABLE}.product_brand ;;
  }

  dimension: product_retail_price {
    type: number
    sql: ${TABLE}.product_retail_price ;;
  }

  dimension: product_department {
    type: string
    sql: ${TABLE}.product_department ;;
  }

  dimension: product_sku {
    type: string
    sql: ${TABLE}.product_sku ;;
  }

  dimension: product_distribution_center_id {
    type: number
    sql: ${TABLE}.product_distribution_center_id ;;
  }

  measure: count {
    type: count
  }

  measure: count_distinct_id {
    type: count_distinct
    sql: ${id} ;;
  }

  measure: sum_cost {
    type: sum
    sql: ${cost} ;;
  }

  measure: avg_cost {
    type: average
    sql: ${cost} ;;
  }

  measure: sum_product_retail_price {
    type: sum
    sql: ${product_retail_price} ;;
  }

  measure: avg_product_retail_price {
    type: average
    sql: ${product_retail_price} ;;
  }
}