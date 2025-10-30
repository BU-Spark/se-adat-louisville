# plumber.r
library(plumber)
library(jsonlite)
library(tidyverse)
library(tidygeocoder)
library(sf)

# ---------- load geography once ----------
# Use the same file you ship with the app. If you have the 2023 BG file from data_prep:
# lvm_bg_geo <- st_read("./data/gis/KY_Jefferson_BG_2023.shp") %>%
#   st_transform(crs = 4326)
# If your app folder has the 2022 file (as in app.r), use this instead:
lvm_bg_geo <- st_read("C:/Users/lunes/Documents/git/DHNA-tool/data/nhgis/gis/tract/ct2023/KY_Jefferson_tract_2023.shp") %>%
  dplyr::filter(COUNTYFP == "111") %>%
  sf::st_transform(crs = 4326)

# ---------- API meta ----------
#* @apiTitle ADAT R Service
#* @apiDescription R endpoints for ADAT

# ---------- health ----------
#* Health
#* @get /health
function() list(status="ok", ts=Sys.time())

# ---------- geocode (POST) ----------
#* Geocode an address (POST JSON: {address, city, state, zip})
#* @post /geocode
function(req, res){
  body <- tryCatch(jsonlite::fromJSON(req$postBody), error=function(e) NULL)
  if (is.null(body)) {
    res$status <- 400
    return(list(status="error", reason="Invalid JSON"))
  }
  if (is.null(body$address) && is.null(body$city) && is.null(body$state) && is.null(body$zip)) {
    res$status <- 400
    return(list(status="error", reason="address/city/state/zip required"))
  }
  addr <- tibble(singlelineaddress = paste(body$address, body$city, body$state, body$zip, sep=", "))
  geo <- tryCatch(addr %>% geocode(address = singlelineaddress, method = "census"),
                  error=function(e) NULL)
  if (is.null(geo) || nrow(geo) == 0 || any(is.na(geo$lat) | is.na(geo$long))) {
    res$status <- 400
    return(list(status="error", reason="Unable to geocode"))
  }
  list(status="ok", lat=geo$lat[[1]], lng=geo$long[[1]])
}

# ---------- geocode (GET helper for browser testing) ----------
#* Geocode an address (GET query: ?address=&city=&state=&zip=)
#* @get /geocode
function(req, res, address="", city="", state="", zip=""){
  addr <- tibble(singlelineaddress = paste(address, city, state, zip, sep=", "))
  geo <- tryCatch(addr %>% geocode(address = singlelineaddress, method = "census"),
                  error=function(e) NULL)
  if (is.null(geo) || nrow(geo) == 0 || any(is.na(geo$lat) | is.na(geo$long))) {
    res$status <- 400
    return(list(status="error", reason="Unable to geocode"))
  }
  list(status="ok", lat=geo$lat[[1]], lng=geo$long[[1]])
}

# ---------- BG lookup ----------
#* Lookup block group (GISJOIN) for a lat/lng
#* @post /bg-lookup
function(req, res){
  body <- tryCatch(jsonlite::fromJSON(req$postBody), error=function(e) NULL)
  if (is.null(body) || is.null(body$lat) || is.null(body$lng)) {
    res$status <- 400
    return(list(status="error", reason="lat/lng required"))
  }
  lat <- suppressWarnings(as.numeric(body$lat))
  lng <- suppressWarnings(as.numeric(body$lng))
  if (is.na(lat) || is.na(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    res$status <- 400
    return(list(status="error", reason="lat/lng invalid")) }
  pt <- st_sfc(st_point(c(lng, lat)), crs = 4326)
  idx <- tryCatch(st_intersects(pt, lvm_bg_geo)[[1]], error=function(e) integer(0))
  if (length(idx) < 1) {
    res$status <- 404
    return(list(status="error", reason="Point not in study area"))
  }
  list(status="ok", gisjoin = lvm_bg_geo$GISJOIN[idx[1]])
}

# ---------- assess ----------
#* Full assessment (front-door for the UI)
#* @post /assess
function(req, res){
  b <- tryCatch(jsonlite::fromJSON(req$postBody), error=function(e) NULL)
  if (is.null(b)) { res$status <- 400; return(list(status="error", reason="Invalid JSON")) }
  
  reqd <- c("session_id","project_name","project_units_total",
                        "affordability","gisjoin","lat","lng")
  miss <- reqd[!reqd %in% names(b)]
  if (length(miss) > 0) {
    res$status <- 400
    return(list(status="error", reason=paste("Missing:", paste(miss, collapse=", "))))
  }
  total_aff <- sum(unlist(b$affordability[c("ami30","ami50","ami60","ami70","ami80")]), na.rm=TRUE)
  if (!is.numeric(b$project_units_total) || total_aff > b$project_units_total) {
    res$status <- 400
    return(list(status="error", reason="affordability exceeds total units or units invalid"))
  }
  
  eligible <- (total_aff >= 0.3 * b$project_units_total)
  
  list(
    status="ok",
    result=list(
      session_id = b$session_id,
      project_name = b$project_name,
      location = list(lat=b$lat, lng=b$lng, gisjoin=b$gisjoin),
      totals = list(units = b$project_units_total, affordable = total_aff),
      decision = list(eligible = eligible,
                      reason = ifelse(eligible,"Meets min affordability","Increase affordable units"))
    )
  )
}





