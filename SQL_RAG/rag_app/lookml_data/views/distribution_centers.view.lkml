view: distribution_centers {
  sql_table_name: `bigquery-public-data.thelook_ecommerce.distribution_centers` ;;

  dimension: id {
    primary_key: yes
    type: number
  }

  dimension: name {
    type: string
    sql: ${TABLE}.name ;;
  }

  dimension: latitude {
    type: number
    sql: ${TABLE}.latitude ;;
  }

  dimension: longitude {
    type: number
    sql: ${TABLE}.longitude ;;
  }

  dimension: distribution_center_geom {
    type: string
    sql: ${TABLE}.distribution_center_geom ;;
  }

  measure: count {
    type: count
  }

  measure: count_distinct_id {
    type: count_distinct
    sql: ${id} ;;
  }

  measure: sum_latitude {
    type: sum
    sql: ${latitude} ;;
  }

  measure: avg_latitude {
    type: average
    sql: ${latitude} ;;
  }

  measure: sum_longitude {
    type: sum
    sql: ${longitude} ;;
  }

  measure: avg_longitude {
    type: average
    sql: ${longitude} ;;
  }
}