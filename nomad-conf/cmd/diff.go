package cmd

import (
	"fmt"
	"os"

	"github.com/gerrowadat/nomad-homelab/nomad-conf/nomadconf"
	"github.com/spf13/cobra"
)

// diffCmd represents the diff command
var diffCmd = &cobra.Command{
	Use:   "diff <local file> <variable>",
	Short: "show differences between a local file and a nomad variable",
	Run: func(cmd *cobra.Command, args []string) {
		doDiff(cmd, args)
	},
}

func init() {
	rootCmd.AddCommand(diffCmd)
}

func doDiff(cmd *cobra.Command, args []string) {
	if len(args) != 2 {
		cmd.Help()
		return
	}
	v := nomadconf.NewVarSpec(args[1])

	filedata, err := os.ReadFile(args[0])
	if err != nil {
		fmt.Printf("Error getting local file contents: %v\n", err)
		cmd.Help()
		return
	}

	n, err := nomadconf.NomadClient(nomadServer)

	if err != nil {
		fmt.Println("Nomad Error:", err)
		return
	}

	diff, err := nomadconf.GetVariableDiff(n, v, string(filedata))

	if err != nil {
		fmt.Println("Error getting diff:", err)
		return
	}

	if diff == "" {
		fmt.Println("No differences found")
		return
	}

	fmt.Println(diff)
}
