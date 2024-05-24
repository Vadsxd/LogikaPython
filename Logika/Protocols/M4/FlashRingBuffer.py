from datetime import datetime
from typing import List

from Logika.Meters.__4L.Logika4L import Logika4L
from Logika.Protocols.M4.FlashArchive4L import FlashArchive4
from Logika.Protocols.M4.M4Protocol import MeterInstance, M4Protocol


class FRBIndex:
    def __init__(self, index, time):
        self.idx = index
        self.time = time

    def __str__(self):
        return "{0}: {1:%d.%m.%Y %H:%M}".format(self.idx, self.time)

    @staticmethod
    def compare_by_idx(a, b):
        return a.idx - b.idx


class ObjCollection:
    def __init__(self, ring_buffer, get_obj_delegate):
        self.parent = ring_buffer
        self.gobj = get_obj_delegate

    def __getitem__(self, index):
        buf, offset = self.parent.get_element(index)
        return self.gobj(self.parent.parent_archive, buf, offset)


class FlashArray:
    def __init__(self, meter_instance: MeterInstance, data_addr: int, element_count: int, element_size: int):
        self.PAGE_SIZE: int = Logika4L.FLASH_PAGE_SIZE
        start_page: int = self.start_page(0)
        self.page_0_number: int = start_page

        self.data_addr: int = data_addr
        self.element_count: int = element_count
        self.element_size: int = element_size
        self.mtr_instance: MeterInstance = meter_instance

        self.flash: bytearray = bytearray()
        self.page_map: List[bool] = []

        self.first_element_offset: int = data_addr - start_page * self.PAGE_SIZE

        self.start_page_elem: int = 0
        self.end_page_elem: int = 0

    def get_element(self, index: int):
        if not self.element_available(index):
            self.update_element_explicit(index)

        buffer = self.flash
        offset = self.first_element_offset + index * self.element_size

        return buffer, offset

    def start_page(self, elementIndex: int):
        return (self.data_addr + elementIndex * self.element_size) // self.PAGE_SIZE

    def end_page(self, elementIndex: int):
        return (self.data_addr + (elementIndex + 1) * self.element_size - 1) // self.PAGE_SIZE

    def element_available(self, index: int):
        sp = self.start_page(index)
        ep = self.end_page(index)
        for p in range(sp, ep + 1):
            if not self.page_map[p - self.page_0_number]:
                return False
        return True

    def invalidate_element(self, index: int):
        sp = self.start_page(index)
        ep = self.end_page(index)
        for p in range(sp, ep + 1):
            self.page_map[p - self.page_0_number] = False

    def update_pages(self, start_page: int, end_page: int):
        page_count = end_page - start_page + 1

        mtr_4L = self.mtr_instance.mtr.__class__ = Logika4L()
        rbuf = self.mtr_instance.proto.read_flash_pages(mtr_4L, self.mtr_instance.nt, start_page, page_count)

        rPage = start_page - self.page_0_number
        self.flash = rbuf
        for v in range(page_count):
            self.page_map[rPage + v] = True

    def update_elements(self, indexes: List[FRBIndex]):
        self.start_page_elem = -1
        self.end_page_elem = -1

        i = 0
        while i < len(indexes):
            esp = self.start_page(indexes[i].idx)  # element start page
            eep = self.end_page(indexes[i].idx)  # element end page
            for p in range(esp, eep + 1):
                if not self.page_map[p - self.page_0_number]:
                    if not self.extend_page_range(p):  # cannot extend page range with this var
                        self.update_pages(self.start_page_elem, self.start_page_elem)
                        indexes = indexes[i:]
                        break
                elif self.end_page_elem != -1 and self.start_page_elem != -1:
                    self.update_pages(self.start_page_elem, self.end_page_elem)
                    indexes = indexes[i:]
                    break
            i += 1

        if self.start_page_elem == -1 or self.end_page_elem == -1:
            indexes.clear()  # no elements need an update

    def update_element_explicit(self, element: int):
        self.update_pages(self.start_page(element), self.end_page(element))

    def extend_page_range(self, page: int):
        if self.start_page == -1 or self.end_page == -1:
            self.start_page_elem = self.end_page_elem = page
            return True

        if page < self.start_page_elem - 1 or page > self.end_page_elem + 1:
            return False

        n_sp = self.start_page_elem
        n_ep = self.end_page_elem

        if page == self.start_page_elem or page == self.start_page_elem - 1:
            n_sp = page
        elif page == self.end_page_elem or page == self.end_page_elem + 1:
            n_ep = page
        else:
            return False

        if n_ep - n_sp >= M4Protocol.MAX_PAGE_BLOCK:
            return False

        self.start_page_elem = n_sp
        self.end_page_elem = n_ep
        return True

    def reset(self):
        self.page_map = []


class FlashRingBuffer(FlashArray):
    def __init__(self, Parent, IndexAddress, DataAddress, ElementCount, ElementSize, HeaderTimeGetter, HeaderValueGetter):
        super().__init__(Parent.mi, DataAddress, ElementCount, ElementSize)
        self.prev_idx: int = -1
        self.ts_prev_idx: datetime = datetime.now()
        self.prevIdx_devTime: datetime = datetime.min
        self.parentArchive: FlashArchive4 = Parent
        self.IndexAddress: int = IndexAddress

        self.Times = ObjCollection(self, HeaderTimeGetter)
        if HeaderValueGetter is not None:
            self.Values = ObjCollection(self, HeaderValueGetter)

        self.percent_completed: int = 0

        self.reset()

    def reset(self):
        super().reset()
        self.prev_idx = -1
        self.ts_prev_idx = None
        self.prevIdx_devTime = datetime.min

    def get_element_indexes_in_range(self, initial_time: datetime, stop_time: datetime, last_written_index: int, restart_point: int, indexes: List[FRBIndex]):
        if restart_point < 0:
            restart_point = last_written_index

        finished = False
        reads_done = 0
        count = (restart_point - last_written_index + self.element_count) % self.element_count
        if count == 0:
            count = self.element_count

        ci = restart_point
        for i in range(count):
            ci = (restart_point - i + self.element_count) % self.element_count
            if self.element_available(ci):
                t = self.Times[ci]
                if t is None:
                    if ci == self.element_count - 1:
                        continue
                    else:
                        finished = True
                        break
                if not t or t == datetime.min:
                    continue
                if initial_time <= t <= stop_time:
                    indexes.append(FRBIndex(ci, t))
                finished = t <= initial_time
                finished |= i == count - 1
                if finished:
                    break
            else:
                if reads_done > 0:
                    break
                elements_left = count - i
                self.start_page_elem = -1
                self.end_page_elem = -1
                for t in range(elements_left):
                    ti = (ci - t + self.element_count) % self.element_count
                    esp = self.start_page(ti)
                    eep = self.end_page(ti)
                    for page in range(eep, esp - 1, -1):
                        if not self.page_map[page - self.page_0_number]:
                            if not self.extend_page_range(page):
                                self.update_pages(self.start_page_elem, self.end_page_elem)
                                reads_done += 1
                                i -= 1

        restart_point = ci
        self.percent_completed = len(indexes) * 100.0 / self.element_count

        if finished:
            indexes.reverse()
            self.percent_completed = 100

        return finished, restart_point

    def manage_outdated_elements(self, use_index_cache: bool):
        outdatedList = []
        cdt = self.parentArchive.mi.current_device_time
        gT = 15
        at_guard_interval = (cdt.minute == 59 and cdt.second > 60 - gT) or (cdt.minute == 0 and cdt.second < gT)

        if use_index_cache and self.prev_idx != -1 and self.prevIdx_devTime != datetime.min:
            if self.prevIdx_devTime.date() == cdt.date() and self.prevIdx_devTime.hour == cdt.hour:
                currentIndex = self.prev_idx
                return outdatedList, currentIndex

        mtr_4L = self.parentArchive.mi.mtr.__class__ = Logika4L()
        ibytes = self.parentArchive.mi.proto.read_flash_bytes(mtr_4L, self.parentArchive.mi.nt, self.IndexAddress, 2)
        currentIndex = int.from_bytes(ibytes, byteorder='little')

        if currentIndex >= self.element_count:
            raise Exception(f"Invalid archive end pointer: ({currentIndex})")

        if self.prev_idx != -1:
            self.update_element_explicit(self.prev_idx)
            prev_ptr_actual_ts = self.Times[self.prev_idx]

            st = 0
            cnt = 0
            invalidateAll = self.ts_prev_idx != prev_ptr_actual_ts

            if invalidateAll:
                st = 0
                cnt = self.element_count
            elif self.prev_idx != currentIndex:
                st = self.prev_idx
                cnt = (currentIndex - self.prev_idx + self.element_count) % self.element_count

            if cnt != 0:
                for i in range(cnt):
                    idx = (st + i) % self.element_count
                    self.invalidate_element(idx)
                    outdatedList.append(idx)

        self.prev_idx = currentIndex
        self.prevIdx_devTime = self.parentArchive.mi.current_device_time if not at_guard_interval else datetime.min
        self.ts_prev_idx = self.Times[currentIndex]

        return outdatedList, currentIndex
