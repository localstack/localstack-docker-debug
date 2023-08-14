{ pkgs ? import <nixpkgs> { } }:
with pkgs;
mkShell {
  buildInputs = [
    docker
    dive
    act
    (python311.withPackages (ps: with ps; [
      dnspython
      dnslib
      ipython
      go
      awscli2
      docker
      pudb
      click
      graphviz
      pytest
    ]))
    watchexec
    graphviz
  ];
  PYTHONBREAKPOINT = "pudb.set_trace";
}
