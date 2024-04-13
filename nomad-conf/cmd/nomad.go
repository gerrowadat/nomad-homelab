package cmd

import (
	"os"
	"strings"

	api "github.com/hashicorp/nomad/api"
)

// A type for a 'variable spec', which can be a bare variable or a variable with a key specified.
type VarSpec struct {
	VarName, KeyName string
}

func NewVarSpec(spec string) *VarSpec {
	fragments := strings.Split(spec, ":")

	if len(fragments) == 1 {
		return &VarSpec{
			VarName: fragments[0],
			KeyName: "",
		}
	}

	if len(fragments) == 2 {
		return &VarSpec{
			VarName: fragments[0],
			KeyName: fragments[1],
		}
	}

	return nil
}

func (vs *VarSpec) IsKeyed() bool {
	return vs.KeyName != ""
}

func NomadClient() (*api.Client, error) {
	secret := GetNomadSecret()
	cf := &api.Config{
		Address:  nomadServer,
		SecretID: secret,
	}
	return api.NewClient(cf)
}

func GetNomadSecret() string {
	return os.Getenv("NOMAD_TOKEN")
}
