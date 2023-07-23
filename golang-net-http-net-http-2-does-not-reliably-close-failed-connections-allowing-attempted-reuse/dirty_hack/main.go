package main

import (
    "context"
    "fmt"
    "net/http"
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

    // build client and request
    client := http.Client{
        Timeout: 5 * time.Second,
    }

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

            // prompt the handler into marking the connection as not
            // being reusable
            req.Header.Set("Connection", "close")
            client.Do(req.WithContext(ctx))
        } else {
            fmt.Println(resp.StatusCode)
        }

        time.Sleep(time.Second)
    }
}

