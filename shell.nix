{ pkgs ? import <nixpkgs> { } }:
with pkgs;
mkShell {
  buildInputs = [
    docker
    dive
    act
    (python311.withPackages (ps: with ps; [
      awscli2
      click
      dnslib
      dnspython
      docker
      flask
      go
      graphviz
      ipython
      pudb
      pytest
    ]))
    watchexec
    graphviz
  ];
  PYTHONBREAKPOINT = "pudb.set_trace";
}
