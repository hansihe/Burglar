#!/bin/bash

MC_VERSION="1.8.8"
MCP_MAPPING="http://export.mcpbot.bspk.rs/mcp_stable/20-1.8.8/mcp_stable-20-1.8.8.zip"

echo "Fetching MC jar..."
wget -O "temp/mc.jar" "http://s3.amazonaws.com/Minecraft.Download/versions/${MC_VERSION}/${MC_VERSION}.jar" || exit $?

echo "Fetching srg..."
wget -O "temp/mcp-srg.zip" "http://export.mcpbot.bspk.rs/mcp/${MC_VERSION}/mcp-${MC_VERSION}-srg.zip" || exit $?

echo "Fetching mapping..."
wget -O "temp/mcp-mapping.zip" $MCP_MAPPING

echo "Extracting srg..."
unzip -o "temp/mcp-srg.zip" joined.srg -d "temp/"

echo "Extracting mapping..."
unzip -o "temp/mcp-mapping.zip" fields.csv methods.csv params.csv -d "temp/"
