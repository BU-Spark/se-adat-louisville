library(plumber)

# Optional: increase JSON/body limit (default is ~5MB; adjust as needed)
options(plumber.maxRequestSize = 10 * 1024^2)  # 10 MB

# Build router from plumber.r
pr <- pr("plumber.r")

# Optional: disable debug logs in prod
if (identical(tolower(Sys.getenv("PLUMBER_DEBUG", "false")), "false")) {
  pr <- pr_set_debug(pr, FALSE)
}

# Run with env overrides; default matches your current settings
host <- Sys.getenv("PLUMBER_HOST", "127.0.0.1")  # use "0.0.0.0" in Docker
port_str <- Sys.getenv("PLUMBER_PORT", "8001")
port <- as.integer(port_str)
if (is.na(port)) {
  stop("PLUMBER_PORT must be a valid integer, got: ", port_str)
}

pr_run(pr, host = host, port = port)



