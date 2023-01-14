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
--

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
    -- ngx.log(ngx.ERR, res.status)
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
        -- ngx.log(ngx.ERR,"No Auth Header")
        ngx.header["X-Fail"] = "mastoapi-no-auth"
        return false
    end

    -- Check the cache
    local cache = ngx.shared.mastowaf_cache
    local cachekey = "auth-" .. auth_header
    local e = cache:get(cachekey)    

    -- See if we hit the cache
    if e ~= nil then
        -- ngx.header['X-Masto-Auth-Cache'] = 'HIT'
        if e == "true" then
            return true
        end
        
        ngx.header["X-Fail"] = "mastoapi-cached-deny"
        return false
    end
    
    -- We got a value, do a test request with it
    local api_req = place_api_request(ngx, auth_header)
    
    if api_req ~= true then
        -- ngx.log(ngx.ERR,"Failed to validate Auth Token")
        ngx.header["X-Fail"] = "mastoapi-token-invalid"
        return false
    end
    
    -- Update the cache
    cache:set(cachekey,tostring(api_req),20) 

    -- Authorise the request
    return true
end


function check_ip(remote_ip, blocked_ips, allowed_ips)
    -- Check whether the remote address exists in either the allow or
    -- the blocklist
    
    if table_contains(allowed_ips, remote_ip) then
        return
    end


    if table_contains(blocked_ips, remote_ip) then
        ngx.header["X-Denied-By"] = "edge mastodon_api_enforce"
        ngx.header["X-Fail"] = "blocklisted-addr"
        ngx.status = 403
        ngx.exit(403)        
    end
end

function check_referer(http_referer, blocked_referrers)
    -- Check whether the request originates from a blocked referer
    --
    -- Note: these kind of checks are trivial to bypass, but better than nothing
    if http_referer == nil then
        return
    end
    
    for k, v in pairs(blocked_referrers) do
        if v ~= "" and strStartsWith(http_referer, v) then
            ngx.header["X-Denied-By"] = "edge mastodon_api_enforce"
            ngx.header["X-Fail"] = "blocklisted-referer"
            ngx.status = 403
            ngx.exit(403)
        end
    end
    
    
end


-- Utility functions

function strSplit(delim,str)
    local t = {}

    for substr in string.gmatch(str, "[^".. delim.. "]*") do
        if substr ~= nil and string.len(substr) > 0 then
            table.insert(t,substr)
        end
    end

    return t
end

function table_contains(tbl, x)
    found = false
	for _, v in pairs(tbl) do
		if v == x then 
            found = true 
        end
	end
	return found
end

function strStartsWith(s, start)
    return s:sub(1, #start) == start
end

-- Main block

-- ngx.log(ngx.ERR,"Loaded")

bipstr = ngx.var.blocked_ips
if bipstr == nil then
    bipstr = ""
end

aipstr = ngx.var.blocked_ips
if aipstr == nil then
    aipstr = ""
end

brefstr = ngx.var.blocked_referrers
if brefstr == nil then
    brefstr = ""
end

-- Split into tables
blocked_ips = strSplit(",", bipstr)
allowed_ips = strSplit(",", aipstr)
blocked_referrers = strSplit(",", brefstr)

-- Get the client IP
client_ip = ngx.var.remote_addr
if ngx.var.use_xff ~= nil then
    -- Downstream needs to ensure this only contains the client IP
    -- any intermediate proxies need to have been stripped
    client_ip = ngx.var.http_x_forwarded_for
end

-- Run IP enforcement
check_ip(client_ip, blocked_ips, allowed_ips)

-- Run Referer enforcement
check_referer(ngx.var.http_referer, blocked_referrers)

-- Run Client enforcement
if ngx.var.api_enforce == "Y" then
    if validateRequest(ngx) ~= true then
        -- ngx.log(ngx.ERR,"Blocking unauthorised request")
        ngx.header["X-Denied-By"] = "edge mastodon_api_enforce"
        ngx.status = 403
        ngx.exit(403)
    end
end

