project_name: "thelook"

include: [
  "/thelook.model.lkml",
  "/views/*.view.lkml"
]

constant: THELOOK_DATASET { value: "bigquery-public-data.thelook_ecommerce" }
