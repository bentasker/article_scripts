/* Cloudflare Worker Public Mastodon API Protection
 * 
 * Hacked together based on the following docs
 * 
 * https://developers.cloudflare.com/workers/examples/fetch-json/
 * https://developers.cloudflare.com/workers/examples/auth-with-headers/
 *
*/


// The origin to send probe requests to
const api_endpoint = "https://1.2.3.4/api/v2/suggestions";

// The host header to include in those requests
const masto_host_head = "mastodon.bentasker.co.uk"

/** 
 * Checks for an Authorization header and (if present) uses it to send a probe
 * to an authenticated origin endpoint to gauge token validity
 * 
 * No token, or invalid token results in a 403
 *
 * TODO: Add caching of results to prevent repeated upstream calls
 *
 */
async function doProbe(request){
    // The "Authorization" header is sent when authenticated.
    if (request.headers.has('Authorization')) {
            // Build a probe request
            const init = {
                headers: {
                'content-type': 'application/json;charset=UTF-8',
                'authorization': request.headers.get('Authorization'),
                'host' : masto_host_head
                },
            };

            const response = await fetch(api_endpoint, init);
            if (response.status == 200){
                return fetch(request);
            }

            // Otherwise, it failed
            return new Response('Invalid auth', {
                status: 403,
            });
        }

        // No auth header
        return new Response('You need to login.', {
        status: 403,
        });
}


/**
 * Receives a HTTP request and replies with a response.
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function handleRequest(request) {
        const { protocol, pathname } = new URL(request.url);
        var resp 
        switch (pathname) {

        case '/api/v1/timelines/public': {
            resp = await doProbe(request);
            return resp;
        }

        case '/api/v1/trends/statuses': {
            resp = await doProbe(request);
            return resp;
        }
        
        case '/api/v1/trends/tags': {
            resp = await doProbe(request);
            return resp;
        }
        
        default:
            return fetch(request);
    }
}


addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});
