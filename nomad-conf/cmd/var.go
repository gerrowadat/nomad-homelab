package cmd

import (
	"fmt"
	"io"
	"log"
	"os"

	"github.com/gerrowadat/nomad-homelab/nomad-conf/nomadconf"
	api "github.com/hashicorp/nomad/api"
	"github.com/spf13/cobra"
)

// varCmd represents the var command
var varCmd = &cobra.Command{
	Use:   "var [get|put] varname",
	Short: "manipulate nomad variables",
	Long: `Get or put or show info on nomad variables.

Example:
nomad-conf var get jobs/myjob/mytask:thing_config
cat myconfigfile | nomad-conf var put jobs/myjob/mytask:thing_config
`,
	Run: func(cmd *cobra.Command, args []string) {
		doVar(cmd, args)
	},
}

func init() {
	rootCmd.AddCommand(varCmd)
}

func doVar(cmd *cobra.Command, args []string) {
	if len(args) < 1 {
		fmt.Println("Error: missing arguments")
		cmd.Help()
		return
	}

	if args[0] == "get" {
		n, err := nomadconf.NomadClient(nomadServer)
		if err != nil {
			fmt.Println("Nomad Error:", err)
			return
		}
		if len(args) == 1 {
			// Spit out all variables
			for _, v := range nomadconf.GetAllVariables(n) {
				fmt.Println(v.Path)
			}
			return
		}
		if len(args) == 2 {
			// Spit out a single variable
			// Spit out as k/v if we specified a bare variable, or the raw contents if we asked for a key
			vs := nomadconf.NewVarSpec(args[1])
			v, err := nomadconf.GetVariable(n, vs)
			if err != nil {
				log.Fatalf("error getting variable: %v", err)
			}
			fmt.Print(nomadconf.VarToString(v, vs))
			return
		}
		// If we get here we've gotten more than one argument, which is wrong
		fmt.Println("Error: too many arguments to 'var get'")
		cmd.Help()
	}

	if args[0] == "put" {
		n, err := nomadconf.NomadClient(nomadServer)
		if err != nil {
			fmt.Println("Nomad Error:", err)
			return
		}
		if len(args) != 2 {
			fmt.Println("Error: wrong number of arguments to 'var put'")
			cmd.Help()
			return
		}
		vs := nomadconf.NewVarSpec(args[1])
		if !vs.IsKeyed() {
			fmt.Println("Error: must specify a key when putting a variable")
			return
		}

		// Read from stdin
		bytes, err := io.ReadAll(os.Stdin)

		if err != nil {
			log.Fatalf("error reading from stdin: %v", err)
		}

		err = nomadconf.UploadNewVar(n, vs, string(bytes))

		if err != nil {
			log.Fatalf("error updating variable: %v", err)
		}
		return
	}

	if args[0] == "create" {
		n, err := nomadconf.NomadClient(nomadServer)
		if err != nil {
			fmt.Println("Nomad Error:", err)
			return
		}
		if len(args) != 2 {
			fmt.Println("Error: wrong number of arguments to 'var create'")
			cmd.Help()
			return
		}
		vs := nomadconf.NewVarSpec(args[1])
		if !vs.IsKeyed() {
			fmt.Println("Error: must create a key when creating a variable.")
			return
		}

		// Read from stdin
		bytes, err := io.ReadAll(os.Stdin)

		if err != nil {
			log.Fatalf("error reading from stdin: %v", err)
		}

		items := map[string]string{vs.KeyName: string(bytes)}

		_, _, err = n.Variables().Create(&api.Variable{Path: vs.VarName, Items: items}, nil)
		if err != nil {
			log.Fatalf("nomad Error: %v", err)
		}
		return
	}
}
