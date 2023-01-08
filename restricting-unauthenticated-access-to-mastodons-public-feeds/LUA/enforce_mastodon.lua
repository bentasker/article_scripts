--
-- enforce_mastodon.lua
--
-- Nginx config requirements
--
-- Following vars must be defined in Nginx config
--
-- $origin Origin IP domain
-- $origin_port Origin Port 
-- $origin_host_header the host header to pass through
-- $origin_do_ssl set to "no" to disable upstream SSL
--
-- It also requires that a shared dict called mastowaf_cache have
-- been defined

-- We rely on https://github.com/ledgetech/lua-resty-http
-- to make the upstream request
local http = require("resty.http")

function place_api_request(ngx, auth_header)
    -- Place a request to the origin using the /api/v2/suggestions endpoint
    --
    -- This path requires authentication, so allows us to verify that a provided
    -- authentication token is valid

    -- Initiate the HTTP connector
    local httpc = http.new()
    
    ok,err = httpc:connect(ngx.var.origin,ngx.var.origin_port)
    if not ok
    then
       ngx.log(ngx.ERR,"Connection Failed")
       return false
    end

    if ngx.var.origin_do_ssl ~= "no" then
        session, err = httpc:ssl_handshake(False, server, false)
        if err ~= nil then
            ngx.log(ngx.ERR,"SSL Handshake Failed")
            return false
        end
    end
    
    headers = {
        ["user-agent"] = "WAF Probe",
        host = ngx.var.origin_host_header,
        Authorization = auth_header 
    }
    
    local res, err = httpc:request {
        path = "/api/v2/suggestions",
        method = 'GET',
        headers = headers
    }

    -- We're done with the connection, send to keepalive pool
    httpc:set_keepalive()

    -- Check the connection worked
    if not res then
        ngx.log(ngx.ERR,"Upstream Request Failed")
        return false
    end
    
    -- Check the status
    if res.status == 200
    then
        -- Authorised!
        return true
    end
    ngx.log(ngx.ERR, res.status)
    return false 
end


function validateRequest(ngx)
    -- The main work horse
    --
    -- Take the Authorization from the request
    -- Deny if there is none
    -- Check cache for that token and return the result
    -- If needed, place upstream request to check that the token is valid
    -- Return true to allow the request, false to deny it
    
    local auth_header = ngx.var.http_authorization
    
    -- Is the header empty/absent?
    if auth_header == nil then
        ngx.log(ngx.ERR,"No Auth Header")
        ngx.header["X-Fail"] = "mastoapi-no-auth"
        return false
    end

    -- Check the cache
    local cache = ngx.shared.mastowaf_cache
    local cachekey = "auth-" .. auth_header
    local e = cache:get(cachekey)    

    -- See if we hit the cache
    if e ~= nil then
        if e == "true" then
            return true
        end
        
        ngx.header["X-Fail"] = "mastoapi-cached-deny"
        return false
    end
    
    -- We got a value, do a test request with it
    local api_req = place_api_request(ngx, auth_header)
    
    if api_req ~= true then
        ngx.log(ngx.ERR,"Failed to validate Auth Token")
        ngx.header["X-Fail"] = "mastoapi-token-invalid"
        return false
    end
    
    -- Update the cache
    -- We cache results for 20 seconds
    cache:set(cachekey,tostring(api_req),20) 

    -- Authorise the request
    return true
end


ngx.log(ngx.ERR,"Loaded")
if validateRequest(ngx) ~= true then
    ngx.log(ngx.ERR,"Blocking unauthorised request")
    ngx.header["X-Denied-By"] = "edge mastodon_api_enforce"
    ngx.status = 403
    ngx.exit(403)
end
