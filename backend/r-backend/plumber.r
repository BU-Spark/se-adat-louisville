# plumber.r
library(plumber)
library(jsonlite)

#* @apiTitle ADAT R Service
#* @apiDescription R endpoints for ADAT

#* Health check
#* @get /health
function() {
  list(status = "ok", ts = Sys.time())
}

#* Example endpoint (POST JSON body)
#* @post /eligibility
function(req) {
  # Expect JSON body: {"affordable_units":0.3}
  body <- tryCatch(jsonlite::fromJSON(req$postBody), error = function(e) list())
  
  au <- body$affordable_units
  if (!is.null(au) && is.numeric(au) && length(au) == 1 && au >= 0 && au <= 1) {
    list(status="ok",
         result=list(eligible = au >= 0.3, affordable_units = au))
  } else {
    list(status="error",
         result=list(eligible = FALSE,
                     reason = "affordable_units missing or out of [0,1]"))
  }
}


