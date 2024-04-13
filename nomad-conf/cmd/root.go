package cmd

import (
	"os"

	"github.com/spf13/cobra"
)

// rootCmd represents the base command when called without any subcommands
var (
	nomadServer string
	rootCmd     = &cobra.Command{
		Use:   "nomad-conf <verb> <arguments>",
		Short: "A nomad variable/configuration population tool",
		Long: `This tool has various convenience functions for interacting
with nomad variables, as well as loading file sinto them.`,
	}
)

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	rootCmd.PersistentFlags().StringVar(&nomadServer, "nomad-server", "http://localhost:4646", "nomad server to talk to")
}
