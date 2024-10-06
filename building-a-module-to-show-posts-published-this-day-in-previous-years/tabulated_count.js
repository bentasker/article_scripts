/** This really (really really) isn't meant for use in production
 * 
 * I put it together to generate a table showing how many posts there were per day 
 * 
 */

d = 1;
max_d = 366;
date = new Date("2024-01-01");
month = 0;

t1 = document.createElement('table');
t1.className = "dates";
tr = document.createElement('tr');
tr.appendChild(document.createElement("th"));
for (var i=1; i<32; i++){
    th = document.createElement("th");
    
    if (i<10){
        th.innerHTML = "0" + i;
    }else{
        th.innerHTML = i;
    }
    tr.appendChild(th);
}


for (var d=0; d < max_d; d++){
    m = date.getMonth()+1;
    if (m != month){
        t1.appendChild(tr);
        tr = document.createElement("tr");
        td = document.createElement("td");
        td.innerHTML = date.toLocaleString('default', { month: 'short' });
        tr.appendChild(td);
        month = m;
    }
    
    td = document.createElement("td");
    td.id = m + "-" + date.getDate();
    td.className = "present"
    
    tr.appendChild(td);
    date.setDate(date.getDate() + 1);
}

t1.appendChild(tr);

document.getElementsByTagName("body")[0].appendChild(t1);

st = document.createElement("style");
st.type = "text/css"
st.innerText = "td.present {background-color: lightgray; border: 1px solid; color: #000} table.dates{width: 50%; margin: 30px;}";
document.getElementsByTagName("head")[0].appendChild(st);



// Fetch a URL and pass the contents into a callback
function fetchPage(e, t, n) {
    var r;
    (r = window.XMLHttpRequest ? new XMLHttpRequest : new ActiveXObject("Microsoft.XMLHTTP")).onreadystatechange = function() {
        4 == r.readyState && (200 == r.status ? t(r.responseText) : n(r.responseText))
    }, r.open("GET", e, !0), r.send()
}

// A failure function to be passed into fetchPage
function errorResult(resp){
    console.log(resp);
}


function onThisDay(resp){    
    j = JSON.parse(resp);
    for (var i=0; i < j.items.length; i++){
        d = new Date(Date.parse(j.items[i].date_published));
        post_day = (d.getMonth()+1) + "-" + d.getDate();
        
        
        td = document.getElementById(post_day);
        if (td.innerHTML.length == 0){
            c = 0;
        }else{
            c = parseInt(td.innerHTML);
        }
        c++;
        td.innerHTML = c;
    }    
}


fetchPage("/feed.json", onThisDay, errorResult)
