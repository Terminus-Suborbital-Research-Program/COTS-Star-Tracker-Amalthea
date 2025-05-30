{ python312Packages, vmbpy }:
let
  pname = "infratracker";
  version = "0.1.0";
  additionalLibraries = with python312Packages; [ aenum numpy ];
  pyreqs = [ vmbpy ] ++ additionalLibraries;

in python312Packages.buildPythonApplication {
  inherit pname version;
  pyproject = false;

  propagatedBuildInputs = pyreqs;

  dontUnpack = true;

  installPhase = ''
    install -Dm755 ${./infratracker.py} $out/bin/infratracker
  '';
}
