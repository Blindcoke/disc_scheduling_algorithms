import sys
from collections import deque


class Cache:

    def __init__(self, total_capacity, right_capacity):
        if right_capacity >= total_capacity:
            raise ValueError("Right capacity must be less than total capacity")
        self.total_capacity = total_capacity
        self.right_capacity = right_capacity
        self.left_capacity = total_capacity - right_capacity
        self.left = []
        self.right = []

    def get(self, sector):
        if sector in self.left:
            self.left.remove(sector)
            self._add_to_right(sector)
            print(
                f"CACHE: Buffer for sector ({sector}) found in left segment; moved to the beginning of right segment"
            )
            return True
        elif sector in self.right:
            self.right.remove(sector)
            self.right.insert(0, sector)
            print(f"CACHE: Buffer for sector ({sector}) refreshed in right segment")
            return True
        print(f"CACHE: Buffer for sector ({sector}) not found in cache")
        return False

    def put(self, sector):
        if sector in self.left or sector in self.right:
            self.get(sector)
            return

        if len(self.left) < self.left_capacity:
            self.left.insert(0, sector)
            print(f"CACHE: Buffer ({sector}) added to the beginning of left segment")
        else:
            evicted = self.left.pop()
            self.left.insert(0, sector)
            print(
                f"CACHE: Buffer ({sector}) added to the beginning of left segment; evicted buffer ({evicted})"
            )

    def _add_to_right(self, sector):
        if len(self.right) < self.right_capacity:
            self.right.insert(0, sector)
        else:
            moved_to_left = self.right.pop()
            self.right.insert(0, sector)
            self.put(moved_to_left)
            print(
                f"CACHE: Buffer ({sector}) added to the beginning of right segment; moved buffer ({moved_to_left}) to left segment"
            )

    def get_cache(self):
        if not self.left and not self.right:
            print("CACHE: Cache is empty")
        else:
            print("CACHE: Current state of the buffer cache:")
            print("    Left segment [", end="")
            print(", ".join(str(sector) for sector in self.left), end="")
            print("]")
            print("    Right segment [", end="")
            print(", ".join(str(sector) for sector in self.right), end="")
            print("]")

    def flush_cache(self):
        print("CACHE: Flushing the cache")
        self.left = []
        self.right = []
        print("CACHE: Current state of the buffer cache:")
        print("    Left segment [", end="")
        print(", ".join(str(sector) for sector in self.left), end="")
        print("]")
        print("    Right segment [", end="")
        print(", ".join(str(sector) for sector in self.right), end="")
        print("]")
        print("CACHE: Cache flushed")


class Process:
    def __init__(self, name: str, operation: str, sector: int):
        self.name = name
        self.operation = operation
        self.sector = sector
        self.state = "ready"


class Scheduler:
    def __init__(self, processes, buffer_cache, driver, system):
        self.processes = processes
        self.buffer_cache = buffer_cache
        self.driver = driver
        self.system = system
        self.scheduler_time = 0
        self.is_busy = True
        self.blocked_processes = dict()

    def print_settings(self):
        print("Settings:")
        print(f"    syscall_read_time   {System.SYSCALL_READ_TIME}")
        print(f"    syscall_write_time  {System.SYSCALL_WRITE_TIME}")
        print(f"    disk_intr_time      {System.DISK_INTR_TIME}")
        print(f"    quantum_time        {System.QUANTUM_TIME}")
        print(f"    before_writing_time {System.BEFORE_WRITING_TIME}")
        print(f"    after_reading_time  {System.AFTER_READING_TIME}")
        print(f"    buffers_num         {System.BUFFERS_NUM}")
        print(f"    tracks_num          {HardDrive.TOTAL_TRACKS}")
        print(f"    sectors_per_track   {HardDrive.SECTORS_PER_TRACK}")
        print(f"    track_seek_time     {HardDrive.TRACK_SEEK_TIME}")
        print(f"    rewind_seek_time    {HardDrive.REWIND_SEEK_TIME}")
        print(f"    rotation_delay_time {HardDrive.ROTATION_DELAY_TIME}")
        print(f"    sector_access_time  {HardDrive.SECTOR_ACCESS_TIME}")

    def driver_check(self, system_time):
        if self.driver.finished_operations:
            sector = self.driver.finished_operations.pop(0)
            print(f"SCHEDULER: {system_time} us: (NEXT ITERATION)")
            system_time += System.DISK_INTR_TIME
            print(f"SCHEDULER: Disk interrupt handler was invoked")
            return sector, system_time
        return None

    def block_process(self, process, sector):
        if sector not in self.blocked_processes:
            self.blocked_processes[sector] = []
        self.blocked_processes[sector].append(process)

    def wake_process(self, process, sector):
        if sector in self.blocked_processes:
            self.blocked_processes[sector].remove(process)

    def update(self, system_time):
        is_interrupted = self.driver_check(system_time)
        if is_interrupted:
            finished_sector, system_time = is_interrupted
            self.buffer_cache.put(finished_sector)
            for process in self.blocked_processes.get(finished_sector, []):
                self.wake_process(process, finished_sector)
                print(f"SCHEDULER: awake {process.name} ")
                if process.operation == "read":
                    self.system.system_time += System.AFTER_READING_TIME
                    print(f"... worked for {System.AFTER_READING_TIME} us (completed)")

        if self.processes:
            process = self.processes.pop(0)
            if process.operation == "write":
                self.system.system_time += System.BEFORE_WRITING_TIME
                print(f"... worked for {System.BEFORE_WRITING_TIME} us (completed)")
            self.system.handle_syscall(process)
            if self.buffer_cache.get(process.sector):  # Cache hit
                print(f"SCHEDULER: Sector {process.sector} found in buffer cache.")
            else:  # Cache miss, add to driver queue
                print(f"SCHEDULER: Adding {process.sector} to driver queue.")
                self.driver.schedule_operation(process.sector)
                self.block_process(process, process.sector)
                print(f"SCHEDULER: Process {process.name} blocked.")
            self.buffer_cache.get_cache()

        self.is_busy = (
            len(self.processes) > 0
            or sum(len(self.blocked_processes[sector]) for sector in self.blocked_processes.keys()) > 0
        )


class HardDrive:
    TOTAL_TRACKS = 10
    SECTORS_PER_TRACK = 500
    TRACK_SEEK_TIME = 500
    REWIND_SEEK_TIME = 10
    ROTATION_DELAY_TIME = 4000
    SECTOR_ACCESS_TIME = 16

    def __init__(self):
        self.current_track = 0
        self.current_sector = 0

    def calculate_track_and_sector(self, global_sector):
        track = global_sector // HardDrive.SECTORS_PER_TRACK
        sector = global_sector % HardDrive.SECTORS_PER_TRACK
        return track, sector

    def move_to_track(self, target_track):
        seek_time = abs(self.current_track - target_track) * HardDrive.TRACK_SEEK_TIME
        print(f"Moving to track {target_track}. Seek time: {seek_time} us")
        self.current_track = target_track
        return seek_time

    def rotate_to_sector(self, target_sector):
        rotation_time = HardDrive.ROTATION_DELAY_TIME
        print(f"Rotating to sector {target_sector}. Rotation time: {rotation_time} us")
        self.current_sector = target_sector
        return rotation_time

    def access_sector(self, target_sector):
        access_time = HardDrive.SECTOR_ACCESS_TIME
        print(f"Accessing sector {target_sector}. Access time: {access_time} us")
        return access_time


class Controller:
    def __init__(self, hard_drive: HardDrive):
        self.hard_drive = hard_drive

    def perform_operation(self, global_sector):
        track, sector = self.hard_drive.calculate_track_and_sector(global_sector)
        seek_time = self.hard_drive.move_to_track(track)
        rotation_time = self.hard_drive.rotate_to_sector(sector)
        access_time = self.hard_drive.access_sector(sector)

        operation_time = seek_time + rotation_time + access_time
        return operation_time


class Driver:
    def __init__(self, device_strategy: str, controller: Controller, max_queue_length: int = 3):
        self.device_strategy = device_strategy
        self.controller = controller
        self.request_queue = []
        self.request_queues = [[]]
        self.max_queue_length = max_queue_length
        self.controller_wait_time = 0
        self.active_buffer = None
        self.finished_operations = []
        self.direction = 1

    def schedule_operation(self, global_sector):
        if self.device_strategy == "NLOOK":
            if not self.request_queues:
                self.request_queues.append([])
            if len(self.request_queues[-1]) >= self.max_queue_length:
                self.request_queues.append([])
            self.request_queues[-1].append(global_sector)
        else:
            self.request_queue.append(global_sector)

    def perform_interruption(self):
        if self.active_buffer:
            print(f"DRIVER: Operation completed for sector {self.active_buffer}")
            self.finished_operations.append(self.active_buffer)
            self.active_buffer = None

    def FIFO(self):
        if not self.active_buffer and self.request_queue:
            global_sector = self.request_queue.pop(0)
            self.active_buffer = global_sector
            self.controller_wait_time = self.controller.perform_operation(global_sector)
            print(f"DRIVER: Performing operation for sector {global_sector}")
            return self.controller_wait_time
        else:
            return 0

    def LOOK(self):
        if not self.active_buffer and self.request_queue:
            self.request_queue.sort()
            current_track = self.controller.hard_drive.current_track
            next_requests = []
            if self.direction > 0:
                next_requests = [
                    req for req in self.request_queue if req >= current_track * HardDrive.TRACK_SEEK_TIME
                ]
            else:
                next_requests = [
                    req for req in self.request_queue if req < current_track * HardDrive.TRACK_SEEK_TIME
                ]
            if not next_requests:
                self.direction *= -1
                if self.direction > 0:
                    next_requests = [
                        req for req in self.request_queue if req >= current_track * HardDrive.TRACK_SEEK_TIME
                    ]
                else:
                    next_requests = [
                        req for req in self.request_queue if req < current_track * HardDrive.TRACK_SEEK_TIME
                    ]

            if not next_requests:
                next_requests = self.request_queue
            if next_requests:
                global_sector = next_requests[0]
                self.request_queue.remove(global_sector)
                self.active_buffer = global_sector
                self.controller_wait_time = self.controller.perform_operation(global_sector)
                print(f"DRIVER: Performing operation for sector {global_sector}")
                return self.controller_wait_time

        return 0

    def NLOOK(self):
        if not self.active_buffer and any(self.request_queues):
            for queue in self.request_queues:
                queue.sort()
            current_track = self.controller.hard_drive.current_track
            while any(self.request_queues):
                oldest_queue = self.request_queues[0]
                next_requests = []
                if self.direction > 0:
                    next_requests = [
                        req for req in oldest_queue if req >= current_track * HardDrive.TRACK_SEEK_TIME
                    ]
                else:
                    next_requests = [
                        req for req in oldest_queue if req < current_track * HardDrive.TRACK_SEEK_TIME
                    ]

                if not next_requests:
                    self.direction *= -1
                    if self.direction > 0:
                        next_requests = [
                            req for req in oldest_queue if req >= current_track * HardDrive.TRACK_SEEK_TIME
                        ]
                    else:
                        next_requests = [
                            req for req in oldest_queue if req < current_track * HardDrive.TRACK_SEEK_TIME
                        ]

                if not next_requests:
                    self.request_queues.pop(0)
                    continue
                global_sector = next_requests[0]
                oldest_queue.remove(global_sector)
                self.active_buffer = global_sector
                self.controller_wait_time = self.controller.perform_operation(global_sector)
                print(f"DRIVER: Performing operation for sector {global_sector}")
                if not oldest_queue:
                    self.request_queues.pop(0)

                return self.controller_wait_time

        return 0


class System:
    DISK_INTR_TIME = 50
    SYSCALL_READ_TIME = 150
    SYSCALL_WRITE_TIME = 150
    QUANTUM_TIME = 2000
    BEFORE_WRITING_TIME = 7000
    AFTER_READING_TIME = 7000
    BUFFERS_NUM = 10

    def __init__(self, device_strategy: str = "FIFO"):
        self.system_time = 0
        self.hard_drive = HardDrive()
        self.controller = Controller(self.hard_drive)
        self.interruptions = deque()
        self.driver = Driver(device_strategy, self.controller)
        self.buffer_cache = Cache(total_capacity=self.BUFFERS_NUM, right_capacity=self.BUFFERS_NUM // 2)
        self.device_strategy = device_strategy
        self.processes = []

    def create_process(self, name: str, operation: str, sector: int):
        process = Process(name, operation, sector)
        self.processes.append(process)

    def handle_syscall(self, process):
        if process.operation == "read":
            self.system_time += System.SYSCALL_READ_TIME
            print(f"SCHEDULER: process {process.name} invoked read() syscall for sector {process.sector}.")
        elif process.operation == "write":
            self.system_time += System.SYSCALL_WRITE_TIME
            print(f"SCHEDULER: process {process.name} invoked write() syscall for sector {process.sector}.")

    def run_simulation(self):
        scheduler = Scheduler(
            processes=self.processes.copy(), buffer_cache=self.buffer_cache, driver=self.driver, system=self
        )
        scheduler.print_settings()

        while scheduler.is_busy:
            if self.interruptions and self.system_time >= self.interruptions[0]:
                print("... Disk interrupt handler invoked at ", self.system_time)
                self.driver.perform_interruption()
                self.interruptions.popleft()
                self.system_time += System.DISK_INTR_TIME
                print(f"... worked for {System.DISK_INTR_TIME} us in disk interrupt handler")
                print(f"\nSYSTEM TIME: {self.system_time} us")
                scheduler.update(self.system_time)

            if self.system_time % System.QUANTUM_TIME == 0:
                scheduler.update(self.system_time)

            if self.device_strategy == "FIFO":
                next_driver_time = self.driver.FIFO()
            elif self.device_strategy == "LOOK":
                next_driver_time = self.driver.LOOK()
            elif self.device_strategy == "NLOOK":
                next_driver_time = self.driver.NLOOK()

            if next_driver_time:
                print(f"DRIVER: Controller will be busy for {next_driver_time} us")
                self.interruptions.append(self.system_time + next_driver_time)
            self.system_time += 1
        print("\nSYSTEM SIMULATION COMPLETE")
        print(f"Total disk operation time: {self.system_time - 1} us")
        self.buffer_cache.flush_cache()


def main():

    system = System(device_strategy=sys.argv[1])

    system.create_process("qqq", "write", sector=100)
    system.create_process("eee", "read", sector=2300)
    system.create_process("www", "read", sector=200)
    system.create_process("bbb", "write", sector=3000)
    system.create_process("aaa", "read", sector=100)
    system.create_process("ccc", "write", sector=2050)
    system.create_process("nnn", "read", sector=228)
    system.create_process("ddd", "write", sector=3000)

    system.run_simulation()


if __name__ == "__main__":
    main()
