{ pkgs ? import <nixpkgs> { } }:
with pkgs;
mkShell {
  buildInputs = [
    docker
    dive
    (python3.withPackages (ps: with ps; [
      dnspython
      dnslib
      ipython
      go
      awscli2
      docker
      pudb
      click
    ]))
    watchexec
  ];
  PYTHONBREAKPOINT = "pudb.set_trace";
}
