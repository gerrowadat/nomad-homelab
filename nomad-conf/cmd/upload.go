/*
Copyright © 2024 NAME HERE <EMAIL ADDRESS>
*/
package cmd

import (
	"fmt"
	"os"

	"github.com/gerrowadat/nomad-homelab/nomad-conf/util"
	"github.com/spf13/cobra"
)

// uploadCmd represents the upload command
var (
	requireChanges bool
	uploadCmd      = &cobra.Command{
		Use:   "upload <local file> <variable>",
		Short: "Upload file contents to a variable",
		Long: `Upload the contents of a file to a nomad variable as specified.
Flags:
	--require-changes
	  - Only upload if the local file differs (default)

Example:
	nomad-conf upload /etc/passwd nomad/jobs/myjob:handypasswords

Note: We do not do any timestamp checking or whatever to see which version is 'newer'. 
If the two data sources differ, we assume the local version is newer.
If you set --require-changes to false, we upload even an unchanged file - depending on your setup,
this may do stuff like HUP daemon processes every time you update or similar.
`,
		Run: func(cmd *cobra.Command, args []string) {
			doUpload(cmd, args)
		},
	}
)

func init() {
	rootCmd.AddCommand(uploadCmd)

	uploadCmd.PersistentFlags().BoolVar(&requireChanges, "require-changes", true, "only upload if local file is different")

}

func doUpload(cmd *cobra.Command, args []string) {
	if len(args) != 2 {
		cmd.Help()
		return
	}
	v := util.NewVarSpec(args[1])

	filedata, err := os.ReadFile(args[0])
	if err != nil {
		fmt.Printf("Error getting local file contents: %v\n", err)
		cmd.Help()
		return
	}

	n, err := util.NomadClient(nomadServer)

	if err != nil {
		fmt.Println("Nomad Error:", err)
		return
	}

	diff, err := util.GetVariableDiff(n, v, string(filedata))

	if err != nil {
		fmt.Printf("Error diffing new content: %v\n", err)
		return
	}

	if diff == "" {
		if requireChanges {
			fmt.Println("No changes detected, skipping upload")
			return
		}
	}

	// At this point, there is a diff, so we upload the new content.
	err = util.UploadNewVar(n, v, string(filedata))

	if err != nil {
		fmt.Printf("Error uploading new content: %v\n", err)
		return
	}
}
