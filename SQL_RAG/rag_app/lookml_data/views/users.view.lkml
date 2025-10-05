view: users {
  sql_table_name: `bigquery-public-data.thelook_ecommerce.users` ;;

  dimension: id {
    primary_key: yes
    type: number
  }

  dimension: first_name {
    type: string
    sql: ${TABLE}.first_name ;;
  }

  dimension: last_name {
    type: string
    sql: ${TABLE}.last_name ;;
  }

  dimension: email {
    type: string
    sql: ${TABLE}.email ;;
  }

  dimension: age {
    type: number
    sql: ${TABLE}.age ;;
  }

  dimension: gender {
    type: string
    sql: ${TABLE}.gender ;;
  }

  dimension: state {
    type: string
    sql: ${TABLE}.state ;;
  }

  dimension: street_address {
    type: string
    sql: ${TABLE}.street_address ;;
  }

  dimension: postal_code {
    type: string
    sql: ${TABLE}.postal_code ;;
  }

  dimension: city {
    type: string
    sql: ${TABLE}.city ;;
  }

  dimension: country {
    type: string
    sql: ${TABLE}.country ;;
  }

  dimension: latitude {
    type: number
    sql: ${TABLE}.latitude ;;
  }

  dimension: longitude {
    type: number
    sql: ${TABLE}.longitude ;;
  }

  dimension: traffic_source {
    type: string
    sql: ${TABLE}.traffic_source ;;
  }

  dimension_group: created_at {
    type: time
    timeframes: [time, date, week, month, year]
    sql: ${TABLE}.created_at ;;
  }

  dimension: user_geom {
    type: string
    sql: ${TABLE}.user_geom ;;
  }

  measure: count {
    type: count
  }

  measure: count_distinct_id {
    type: count_distinct
    sql: ${id} ;;
  }

  measure: sum_age {
    type: sum
    sql: ${age} ;;
  }

  measure: avg_age {
    type: average
    sql: ${age} ;;
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