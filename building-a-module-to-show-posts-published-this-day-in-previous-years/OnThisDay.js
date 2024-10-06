/** On-This-Day 

Fetch a JSONfeed listing and calculate which
posts were published on this day in prior years.

Update a div to contain a list of them

Assuming you already have a JSONfeed available at /feed.json
all you should need to do is

   * Add a div to your template with id on-this-day
   * Add this script
   
*/

/** Fetch a path (e) and call a callback function (t)
 on error, call error function (n)
 
 Something like this *probably* already exists in any
 libraries you're using and can easily be replaced with
 one.
*/
function fetchPage(e, t, n) {
    var r;
    (r = window.XMLHttpRequest ? new XMLHttpRequest : new ActiveXObject("Microsoft.XMLHTTP")).onreadystatechange = function() {
        4 == r.readyState && (200 == r.status ? t(r.responseText) : n(r.responseText))
    }, r.open("GET", e, !0), r.send()
}

// Callback to be called if the request fails
function errorResult(resp){
    console.log(resp);
}


/** Parse a JSONFeed format response 
    and iterate through items looking for any published
    on this day of the year.
  
    Pass matches onto a function for rendering
*/
function onThisDay(resp){
    var d = new Date();
    var today = (d.getMonth()+1) + "-" + d.getDate();
    var matches = [];
    
    j = JSON.parse(resp);
    for (var i=0; i < j.items.length; i++){
        d = new Date(Date.parse(j.items[i].date_published));
        post_day = (d.getMonth()+1) + "-" + d.getDate();
        
        if (post_day == today){
            j.items[i].isoDate = d.toISOString().split('T')[0]
            matches.push(j.items[i])
        }
    }
    
    if (matches.length > 0){
        writeModule(matches);
    }
}

/** Inject HTML into the DOM to display matches
*
*/
function writeModule(matches){
    var container = document.getElementById('on-this-day');   
    
    h3 = document.createElement('h3');
    h3.innerText = "On This Day";
    container.appendChild(h3);
    
    // Iterate through the matches, appending them
    ul = document.createElement('ul');
    
    cnt = 0;
    for (i=0; i<matches.length; i++){
        li = document.createElement('li');

        a = document.createElement('a');
        a.href = matches[i].url;
        a.appendChild(document.createTextNode(matches[i].title));
        li.appendChild(a);

        li.appendChild(document.createTextNode(" (" + matches[i].isoDate + ")"));
        
        ul.appendChild(li);
        
        // Limit to 5 posts
        cnt++;
        if (cnt >= 5){
            break;
        }
    }
    
    container.appendChild(ul);
    container.appendChild(
        document.createTextNode(
                matches.length + 
                " posts were published on this day of the year"
            )
        );
}


/** Trigger the functionality
*
* Check whether the output div exists
* if not, don't bother doing anything
*
*/
if (document.getElementById('on-this-day')){
    fetchPage("/feed.json", onThisDay, errorResult)
}
