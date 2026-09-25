{ 
  python3Packages 
}:
let
  pyprojectToml = builtins.fromTOML (builtins.readFile ./pyproject.toml);
in
python3Packages.buildPythonPackage {
  pname = pyprojectToml.project.name;
  version = pyprojectToml.project.version;

  src = ./.;

  pyproject = true;

  dependencies = with python3Packages; [
    click
  ];

  build-system = with python3Packages; [
    setuptools
  ];

  doCheck = false;
}
