import subprocess


class BaseProvider():
    def blueprint(self):
        # Default provider doesn't have a blueprint
        return None

    def update_health(self, health):
        i = 2  # we start adding the queues from 1:2, as 1:1 is the default queue
        flow_count = len(health['peers']) + len(health['clients']) + 1
        if flow_count < 2:
            flow_count = 2

        result = ''
        result += self.run(
            ["./scripts/clear_hs_peer_health.sh", str(flow_count)]
        )
        for peer in health['peers']:
            mac = peer['peer']['mac'].split(":")
            result += self.run(
                ["./scripts/set_hs_peer_health.sh", str(i)] +
                mac +
                [str(peer['bandwidth']), str(
                    peer['latency']), str(peer['jitter'])]
            )
            i = i + 1

        for client in health['clients']:
            result += self.run(
                ["./scripts/set_client_health.sh", str(i), str(client.get('source_port', 0))] +
                [str(client['bandwidth']), str(
                    client['latency']), str(client['jitter'])]
            )

        return result

    def run(self, cmd):
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        result = "\n>>> " + ' '.join(cmd)
        if out.stdout:
            result += "\n<<<\n" + out.stdout
        if out.stderr:
            result += "\n<!!\n" + out.stderr
        return result
