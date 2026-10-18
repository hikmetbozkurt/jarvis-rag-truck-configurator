library(jsonlite)

resolve_output_directory <- function() {
  output_directory <- Sys.getenv("JARVIS_DATA_DIR", unset = file.path("..", "data"))
  dir.create(output_directory, showWarnings = FALSE, recursive = TRUE)
  output_directory
}

write_dataset <- function(dataset, file_name) {
  output_path <- file.path(resolve_output_directory(), file_name)
  write_json(dataset, output_path, pretty = TRUE, auto_unbox = TRUE, na = "null")
  message(sprintf("Wrote %s", output_path))
  invisible(output_path)
}

read_dataset <- function(file_name) {
  input_path <- file.path(resolve_output_directory(), file_name)
  if (!file.exists(input_path)) {
    stop(sprintf("%s not found. Run generate_vehicle_catalog.R first.", input_path))
  }
  fromJSON(input_path, simplifyVector = FALSE)
}
