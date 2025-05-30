{
  description = "COTS Infrared Star Tracker for Spacecraft Systems.";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    vimbax.url = "github:Terminus-Suborbital-Research-Program/vimba-x";
  };

  outputs = { self, nixpkgs, flake-utils, vimbax }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Vimba libs
        vimbax-lib = vimbax.packages.${system}.vimbax;

        # Vmbpy lib
        vmbpy = vimbax.packages.${system}.vmbpy;

        infratracker = pkgs.callPackage ./infratracker.nix { inherit vmbpy; };

        # Additional libraries
        additionalLibraries = with pkgs.python312Packages; [ aenum numpy ];

        allPythonLibs = [ vmbpy ] ++ additionalLibraries;
      in {
        packages = { inherit infratracker; };

        devShells.default = pkgs.mkShell {
          buildInputs =
            [ (pkgs.python312.withPackages (ps: allPythonLibs)) vimbax-lib ];
        };
      });
}
