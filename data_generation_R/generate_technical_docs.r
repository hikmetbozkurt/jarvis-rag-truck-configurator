#getwd()

library(jsonlite)
library(dplyr)
library(glue)

# 1. Load the knowledge base we just created
kb <- fromJSON("../data/vehicle_knowledge_base.json")

# 2. Generate "Technical Product Sheets"
# We will create a narrative for each model to help the RAG embeddings
generate_narrative <- function() {
  docs <- list()
  
  # Generate documentation for Models
  for(i in 1:nrow(kb$parts$models)) {
    model <- kb$parts$models[i,]
    docs[[length(docs) + 1]] <- list(
      title = paste("Technical Specification:", model$name),
      content = glue("The {model$name} is classified as a {model$category} vehicle. 
                      {model$description} It is engineered for professional grade 
                      performance in its respective class.")
    )
  }
  
  # Generate documentation for Applications (Industry Knowledge)
  for(i in 1:nrow(kb$parts$applications)) {
    app <- kb$parts$applications[i,]
    docs[[length(docs) + 1]] <- list(
      title = paste("Application Guide:", app$name),
      content = glue("When configuring for {app$name} operations, factors like 
                      chassis durability and torque management are critical. 
                      {app$description} Our engineering team recommends specific 
                      drivetrain combinations for this use case.")
    )
  }
  
  return(docs)
}

# 3. Create a "Consolidated Technical Manual"
technical_manual <- generate_narrative()

# 4. Export as a separate JSON for the RAG system
write_json(technical_manual, "../data/technical_manual.json", pretty = TRUE, auto_unbox = TRUE)

print("Technical Manual (RAG Knowledge) generated successfully!")
