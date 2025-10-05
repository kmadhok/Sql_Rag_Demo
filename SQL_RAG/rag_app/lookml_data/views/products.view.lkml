view: products {
  sql_table_name: `bigquery-public-data.thelook_ecommerce.products` ;;

  dimension: id {
    primary_key: yes
    type: number
  }

  dimension: cost {
    type: number
    sql: ${TABLE}.cost ;;
  }

  dimension: category {
    type: string
    sql: ${TABLE}.category ;;
  }

  dimension: name {
    type: string
    sql: ${TABLE}.name ;;
  }

  dimension: brand {
    type: string
    sql: ${TABLE}.brand ;;
  }

  dimension: retail_price {
    type: number
    sql: ${TABLE}.retail_price ;;
  }

  dimension: department {
    type: string
    sql: ${TABLE}.department ;;
  }

  dimension: sku {
    type: string
    sql: ${TABLE}.sku ;;
  }

  dimension: distribution_center_id {
    type: number
    sql: ${TABLE}.distribution_center_id ;;
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

  measure: sum_retail_price {
    type: sum
    sql: ${retail_price} ;;
  }

  measure: avg_retail_price {
    type: average
    sql: ${retail_price} ;;
  }
}