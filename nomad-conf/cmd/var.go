package cmd

import (
	"fmt"
	"io"
	"log"
	"os"

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
		n, err := NomadClient()
		if err != nil {
			fmt.Println("Nomad Error:", err)
			return
		}
		if len(args) == 1 {
			// Spit out all variables
			ls, _, err := n.Variables().List(nil)
			if err != nil {
				log.Fatalf("nomad Error: %v", err)
			}
			for _, v := range ls {
				fmt.Println(v.Path)
			}
			return
		}
		if len(args) == 2 {
			// Spit out a single variable
			// Spit out as k/v if we specified a bare variable, or the raw contents if we asked for a key
			vs := NewVarSpec(args[1])
			v, _, err := n.Variables().Read(vs.VarName, nil)
			if err != nil {
				log.Fatalf("nomad Error: %v", err)
				return
			}

			if vs.IsKeyed() {
				val, ok := v.Items[vs.KeyName]
				if !ok {
					log.Fatalf("Key %v not found in variable %v", vs.KeyName, vs.VarName)
				}
				fmt.Println(val)
				return
			}

			for k, v := range v.Items {
				fmt.Printf("%v = %v\n", k, v)
			}
			return
		}
		// If we get here we've gotten more than one argument, which is wrong
		fmt.Println("Error: too many arguments to 'var get'")
		cmd.Help()
	}

	if args[0] == "put" {
		n, err := NomadClient()
		if err != nil {
			fmt.Println("Nomad Error:", err)
			return
		}
		if len(args) != 2 {
			fmt.Println("Error: wrong number of arguments to 'var put'")
			cmd.Help()
			return
		}
		vs := NewVarSpec(args[1])
		if !vs.IsKeyed() {
			fmt.Println("Error: must specify a key when putting a variable")
			return
		}

		// Read from stdin
		bytes, err := io.ReadAll(os.Stdin)

		if err != nil {
			log.Fatalf("error reading from stdin: %v", err)
		}

		v, _, err := n.Variables().Read(vs.VarName, nil)
		if err != nil {
			log.Fatalf("nomad Error: %v", err)
		}
		_, ok := v.Items[vs.KeyName]
		if !ok {
			log.Fatalf("Key %v not found in variable %v", vs.KeyName, vs.VarName)
		}
		v.Items[vs.KeyName] = string(bytes)
		_, _, err = n.Variables().Update(v, nil)
		if err != nil {
			log.Fatalf("nomad Error: %v", err)
		}
		return
	}

	if args[0] == "create" {
		n, err := NomadClient()
		if err != nil {
			fmt.Println("Nomad Error:", err)
			return
		}
		if len(args) != 2 {
			fmt.Println("Error: wrong number of arguments to 'var create'")
			cmd.Help()
			return
		}
		vs := NewVarSpec(args[1])
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
