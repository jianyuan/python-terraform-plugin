TF_PLUGIN_PROTOCOL ?= 5.1

default:

protos-download:
	curl -o terraform/protos/grpc_controller.proto https://raw.githubusercontent.com/hashicorp/go-plugin/master/internal/plugin/grpc_controller.proto
	curl -o terraform/protos/tfplugin$(subst .,_,$(TF_PLUGIN_PROTOCOL)).proto https://raw.githubusercontent.com/hashicorp/terraform/master/docs/plugin-protocol/tfplugin${TF_PLUGIN_PROTOCOL}.proto

protos: protos-download
	python -m grpc_tools.protoc -I. --python_out=. --python_grpc_out=. ./terraform/protos/grpc_controller.proto
	python -m grpc_tools.protoc -I. --python_out=. --python_grpc_out=. ./terraform/protos/tfplugin$(subst .,_,$(TF_PLUGIN_PROTOCOL)).proto
