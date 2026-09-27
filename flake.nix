{
  description = "Alidade";
  inputs = {
    nixpkgs.url = "nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils, ... }: utils.lib.eachDefaultSystem (system:
  let
    pkgs = import nixpkgs {
      inherit system;
      overlays = [
        (self: super: {
          mkdocs-fetch-files-plugin = super.callPackage ./nix/mkdocs-fetch-files { };
          kicanvas = super.callPackage ./nix/kicanvas.nix { };
        })
      ];
    };
  in {
    packages.pkgs = pkgs;
    packages.t = pkgs.callPackage ./nix/kicanvas.nix { };
    packages.hw = pkgs.callPackage ./hw { };
    packages.docs = pkgs.callPackage ./docs { alidade-hw = self.packages.${system}.hw; };
    packages.parse-kicad-results = pkgs.callPackage ./nix/parse-kicad-results { };
  });
}
