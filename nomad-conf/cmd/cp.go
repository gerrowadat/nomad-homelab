package cmd

import (
	"fmt"

	"github.com/gerrowadat/nomad-homelab/nomad-conf/nomadconf"
	"github.com/spf13/cobra"
)

// cpCmd represents the cp command
var cpCmd = &cobra.Command{
	Use:   "cp <src> <dest>",
	Short: "Make copies of variables",
	Long: `Copy either an entire variable, or a key.
	
# copy a variable
nomad-conf cp nomad/jobs/myoldjob /nomad/jobs/mynewjob

# copy a variable key
nomad-conf cp nomad/jobs/myjob:thisvar /nomad/jobs/otherjob:thatvar

cp will delete and overwrite an existing key.`,
	Run: func(cmd *cobra.Command, args []string) {
		doCp(cmd, args)
	},
}

func init() {
	rootCmd.AddCommand(cpCmd)
}

func doCp(cmd *cobra.Command, args []string) {
	if len(args) != 2 {
		cmd.Help()
		return
	}
	from := nomadconf.NewVarSpec(args[0])
	to := nomadconf.NewVarSpec(args[1])

	n, err := nomadconf.NomadClient(nomadServer)

	if err != nil {
		fmt.Printf("Nomad error: %v\n", err)
	}

	err = nomadconf.ReplaceVar(n, from, to, true)

	if err != nil {
		fmt.Printf("cp: %v\n", err)
	}
}
