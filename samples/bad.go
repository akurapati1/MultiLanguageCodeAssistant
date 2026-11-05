package main

import "fmt"

func main() {
	_ = doWork()
	fmt.Println("done")
	go func() { panic("boom") }()
}
