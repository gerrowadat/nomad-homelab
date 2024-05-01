package nomadconf

import (
	"fmt"
	"os"
	"strings"

	"github.com/akedrou/textdiff"
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

func NomadClient(server string) (*api.Client, error) {
	secret := GetNomadSecret()
	cf := &api.Config{
		Address:  server,
		SecretID: secret,
	}
	return api.NewClient(cf)
}

func GetNomadSecret() string {
	return os.Getenv("NOMAD_TOKEN")
}

func GetAllVariables(c *api.Client) []*api.VariableMetadata {
	ls, _, _ := c.Variables().List(nil)
	return ls
}

func GetVariable(c *api.Client, vs *VarSpec) (*api.Variable, error) {
	v, _, err := c.Variables().Read(vs.VarName, nil)
	if err != nil {
		return nil, err
	}
	return v, nil
}

func VarToString(v *api.Variable, vs *VarSpec) string {
	if vs.IsKeyed() {
		ret, ok := v.Items[vs.KeyName]
		if !ok {
			return ""
		}
		return ret
	}
	// bare variable, print all the items k = v
	ret := ""
	for k, v := range v.Items {
		ret += fmt.Sprintf("%v = %v\n", k, v)
	}
	return ret
}

func GetVariableDiff(c *api.Client, vs *VarSpec, new_var string) (string, error) {
	// Return a text unified diff of the existing variable vs. candidate content.
	// If the variable does not exist, return a diff that will create it.
	// If the variable exists and is the same, return an empty string.
	if !vs.IsKeyed() {
		return "", fmt.Errorf("variable %v: must specify a key", vs.VarName)
	}
	v, err := GetVariable(c, vs)
	if err != nil {
		return "", fmt.Errorf("variable %v does not exist", vs.VarName)
	}

	if v.Items[vs.KeyName] == new_var {
		// no change
		return "", nil
	}

	d := textdiff.Unified("nomad", "local", v.Items[vs.KeyName], new_var)

	return d, nil
}

func UploadNewVar(c *api.Client, vs *VarSpec, new_var string) error {
	// Upload a new variable with the specified content.
	// If the variable already exists, this will overwrite it.
	// If the variable does not exist, this will create it.
	if !vs.IsKeyed() {
		return fmt.Errorf("variable %v: must specify a key", vs.VarName)
	}
	v, err := GetVariable(c, vs)
	if err != nil {
		return fmt.Errorf("variable %v does not exist", vs.VarName)
	}

	v.Items[vs.KeyName] = new_var

	_, _, err = c.Variables().Update(v, nil)
	return err
}
