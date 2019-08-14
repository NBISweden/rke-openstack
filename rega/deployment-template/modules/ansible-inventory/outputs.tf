output "inventory" {
    value = "${data.template_file.inventory.rendered}"
}
