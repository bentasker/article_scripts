package main

// Change: add net/http2
import (
    "context"
    "fmt"
    "net/http"
    "golang.org/x/net/http2"
    "time"
    "strings"
)

func main() {

    // The url to place requests to
    url := "https://www.bentasker.co.uk/"

    // Create an empty context
    ctx := context.Background()

    // Create an io.Reader from a string to act as the request body
    bodystring := "foo\nbar\nsed"
    myReader := strings.NewReader(bodystring)


    // CHANGES ARE HERE
    
    // Create a transport
    transport := &http.Transport{}

	// Get a copy of the HTTP2 transport
	http2Transport, err := http2.ConfigureTransports(transport)
	if err == nil {
        http2Transport.ReadIdleTimeout = time.Second * 5
        // Change from the default of 15s
        http2Transport.PingTimeout = time.Second * 2
	}

    // build client and request, this time passing the transport in
    client := http.Client{
        Timeout: 5 * time.Second,
        Transport: transport,
    }

    // CHANGES END

    // Set up an infinite loop to place requests from
    for {
        req, err := http.NewRequest("POST", url, myReader)
        if err != nil {
            fmt.Println("boo")
        }
        req.Header.Set("Content-Type", "text/plain; charset=utf-8")

        resp, err := client.Do(req.WithContext(ctx))

        if err != nil {
            // Attempt to tear down the connection
            fmt.Println("Timed out")
            client.CloseIdleConnections()
        } else {
            fmt.Println(resp.StatusCode)
        }

        time.Sleep(time.Second)
    }
}

