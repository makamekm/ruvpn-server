{
    print
    if ($0 == "\"require view.podkop.main as main\";") {
        print "\"require view.rupn.podkop as rupn\";"
        imports++
    }
    if ($0 == "  o.default = \"url\";")
        after_default = 1
    else if (after_default && $0 == "  o.depends(\"connection_type\", \"proxy\");") {
        print "  rupn.addConnectionPicker(section);"
        pickers++
        after_default = 0
    }
}
END {
    if (imports != 1 || pickers != 1)
        exit 1
}
