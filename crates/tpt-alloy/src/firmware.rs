use crate::partition::Partition;
use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum FirmwareTarget {
    Esp32,
    Rp2040,
    RiscV,
}

impl fmt::Display for FirmwareTarget {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FirmwareTarget::Esp32 => write!(f, "esp32"),
            FirmwareTarget::Rp2040 => write!(f, "rp2040"),
            FirmwareTarget::RiscV => write!(f, "riscv"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirmwareBundle {
    pub node_id: usize,
    pub target: FirmwareTarget,
    pub source_code: String,
    pub config_json: String,
}

pub fn generate_firmware(partition: &Partition, target: &FirmwareTarget) -> FirmwareBundle {
    let source = match target {
        FirmwareTarget::Esp32 => generate_esp32_firmware(partition),
        FirmwareTarget::Rp2040 => generate_rp2040_firmware(partition),
        FirmwareTarget::RiscV => generate_riscv_firmware(partition),
    };

    let config = serde_json::json!({
        "node_id": partition.node_id,
        "layers": partition.assigned_layers,
        "cross_edges": partition.cross_node_edges.len(),
    });

    FirmwareBundle {
        node_id: partition.node_id,
        target: target.clone(),
        source_code: source,
        config_json: serde_json::to_string_pretty(&config).unwrap(),
    }
}

fn generate_esp32_firmware(partition: &Partition) -> String {
    format!(
        r#"// Auto-generated ESP32 firmware for node {}
// Layers: {:?}
#include <Arduino.h>

void setup() {{
    Serial.begin(115200);
    Serial.println("TPT Alloy node {} starting");
}}

void loop() {{
    // inference loop placeholder
    delay(100);
}}
"#,
        partition.node_id, partition.assigned_layers, partition.node_id
    )
}

fn generate_rp2040_firmware(partition: &Partition) -> String {
    format!(
        r#"// Auto-generated RP2040 firmware for node {}
// Layers: {:?}
#include "pico/stdlib.h"

int main() {{
    stdio_init_all();
    printf("TPT Alloy node {} starting\n");
    while (true) {{
        // inference loop placeholder
        sleep_ms(100);
    }}
    return 0;
}}
"#,
        partition.node_id, partition.assigned_layers, partition.node_id
    )
}

fn generate_riscv_firmware(partition: &Partition) -> String {
    format!(
        r#"// Auto-generated RISC-V firmware for node {}
// Layers: {:?}
#include <stdio.h>

int main() {{
    printf("TPT Alloy node {} starting\n");
    while (1) {{
        // inference loop placeholder
    }}
    return 0;
}}
"#,
        partition.node_id, partition.assigned_layers, partition.node_id
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::partition::Partition;

    #[test]
    fn test_esp32_firmware_gen() {
        let partition = Partition {
            node_id: 0,
            assigned_layers: vec![0, 1],
            cross_node_edges: vec![],
        };
        let bundle = generate_firmware(&partition, &FirmwareTarget::Esp32);
        assert_eq!(bundle.node_id, 0);
        assert!(bundle.source_code.contains("ESP32"));
    }
}
