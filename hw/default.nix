{
  stdenvNoCC,
  python3Packages,
  ocamlPackages,
  freecad,
}:
stdenvNoCC.mkDerivation {
  name = "alidade-hw";
  src = ./.;
  buildInputs = [
    ocamlPackages.sexp
    freecad
  ] ++ (with python3Packages; [
    kicad
    click
    sexpdata
    ezdxf
  ]);
  preBuild = ''
    export HOME=$(mktemp -d)
  '';
  makeFlags = ''
    PREFIX=$$out
  '';
}
