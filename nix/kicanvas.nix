{
  buildNpmPackage,
  fetchFromGitHub
}:
buildNpmPackage rec {
  pname = "kicanvas";
  version = "b031159eb74aaa7eef2b026fd85d35bc05ff2095";
  src = fetchFromGitHub {
    owner = "theacodes";
    repo = pname;
    rev = version;
    sha256 = "sha256-1qYRqicShJu0Z912X1VOBTGkgqL3QX5ic0VskxJ7SIE=";
  };
  npmDepsHash = "sha256-pWxluQVayUkRtg66kSLM6UReBPoGRF7n50+iS6lktMw=";
  npmBuildScript = "build";
  installPhase = ''
    mkdir -p $out
    cp build/kicanvas.js $out
  '';
}
