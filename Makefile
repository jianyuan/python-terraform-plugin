TF_PLUGIN_PROTOCOL ?= 5.1

default:

protos-download:
	curl -o terraform/protos/grpc_controller.proto https://raw.githubusercontent.com/hashicorp/go-plugin/master/internal/plugin/grpc_controller.proto
	curl -o terraform/protos/tfplugin${TF_PLUGIN_PROTOCOL}.proto https://raw.githubusercontent.com/hashicorp/terraform/master/docs/plugin-protocol/tfplugin${TF_PLUGIN_PROTOCOL}.proto