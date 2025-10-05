connection: "bigquery_conn"
label: "TheLook"
include: ["/views/*.view.lkml"]

explore: users {
  label: "Ecommerce Core"
  description: "User → Orders → Order Items → Products"

  join: orders {
    type: left_outer
    relationship: one_to_many
    sql_on: ${orders.user_id} = ${users.id} ;;
  }

  join: order_items {
    type: left_outer
    relationship: one_to_many
    required_joins: [orders]
    sql_on: ${order_items.order_id} = ${orders.order_id} ;;
  }

  join: products {
    type: left_outer
    relationship: many_to_one
    required_joins: [order_items]
    sql_on: ${order_items.product_id} = ${products.id} ;;
  }
}

explore: inventory_items {
  label: "Operations Core"
  description: "Inventory Items → Products → Distribution Centers"

  join: products {
    type: left_outer
    relationship: many_to_one
    sql_on: ${inventory_items.product_id} = ${products.id} ;;
  }

  join: distribution_centers {
    type: left_outer
    relationship: many_to_one
    required_joins: [products]
    sql_on: ${products.distribution_center_id} = ${distribution_centers.id} ;;
  }
}

explore: orders {
  label: "Orders (Base)"
  join: users {
    type: left_outer
    relationship: many_to_one
    sql_on: ${orders.user_id} = ${users.id} ;;
  }
  join: order_items {
    type: left_outer
    relationship: one_to_many
    sql_on: ${order_items.order_id} = ${orders.order_id} ;;
  }
  join: products {
    type: left_outer
    relationship: many_to_one
    required_joins: [order_items]
    sql_on: ${order_items.product_id} = ${products.id} ;;
  }
}


explore: order_items {
  label: "Order Items (Base)"
  join: orders {
    type: left_outer
    relationship: many_to_one
    sql_on: ${order_items.order_id} = ${orders.order_id} ;;
  }
  join: users {
    type: left_outer
    relationship: many_to_one
    sql_on: ${order_items.user_id} = ${users.id} ;;
  }
  join: products {
    type: left_outer
    relationship: many_to_one
    sql_on: ${order_items.product_id} = ${products.id} ;;
  }
}

explore: products {
  label: "Products (Base)"
  join: order_items {
    type: left_outer
    relationship: one_to_many
    sql_on: ${order_items.product_id} = ${products.id} ;;
  }
  join: orders {
    type: left_outer
    relationship: one_to_many
    required_joins: [order_items]
    sql_on: ${order_items.order_id} = ${orders.order_id} ;;
  }
  join: distribution_centers {
    type: left_outer
    relationship: many_to_one
    sql_on: ${products.distribution_center_id} = ${distribution_centers.id} ;;
  }
  join: inventory_items {
    type: left_outer
    relationship: one_to_many
    sql_on: ${inventory_items.product_id} = ${products.id} ;;
  }
}


explore: distribution_centers {
  label: "Distribution Centers (Base)"
  join: products {
    type: left_outer
    relationship: one_to_many
    sql_on: ${distribution_centers.id} = ${products.distribution_center_id} ;;
  }
  join: inventory_items {
    type: left_outer
    relationship: one_to_many
    # Safe direct key present in inventory_items
    sql_on: ${distribution_centers.id} = ${inventory_items.product_distribution_center_id} ;;
  }
}

explore: events {
  label: "Events (Base)"
  join: users {
    type: left_outer
    relationship: many_to_one
    sql_on: ${events.user_id} = ${users.id} ;;
  }
}