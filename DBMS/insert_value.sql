-- route(các tuyến)
INSERT INTO routes (route_name, start_point, end_depot) VALUES
('BX Mien Tay - An Suong', 'Ben xe Mien Tay', 'Ben xe An Suong'),
('BX Mien Tay - Cho Lon', 'Ben xe Mien Tay', 'Cho Lon'),
('BX Mien Dong - An Suong', 'Ben xe Mien Dong', 'Ben xe An Suong'),
('CV Gia Dinh - Cho Lon', 'Cong vien Gia Dinh', 'Cho Lon');

--stop: các điểm dừng
INSERT INTO stops (stop_name, lat, lon) VALUES
('Ben xe Mien Tay', 10.7416, 106.6354),
('Cong vien Dam Sen', 10.7629, 106.6333),
('San van dong Phu Tho', 10.7769, 106.6675),
('Nga Sau Dan Chu', 10.7722, 106.6694),
('Cong vien Gia Dinh', 10.8126, 106.6786),
('San bay Tan Son Nhat', 10.8188, 106.6520),
('Quang Trung', 10.8357, 106.6411),
('Ben xe An Suong', 10.8443, 106.6056),

('Dai hoc Bach Khoa', 10.7720, 106.6602),
('Benh vien Cho Ray', 10.7536, 106.6610),
('An Dong', 10.7501, 106.6572),
('Cho Lon', 10.7546, 106.6631),

('Ben xe Mien Dong', 10.8026, 106.7146),
('Nga Tu Hang Xanh', 10.8019, 106.7106);

--route_stop: các tuyến

--tuyến 1: BX Miền Tây --> An Sương
INSERT INTO route_stops (route_id, stop_id, stop_order) VALUES
(1, 1, 1),
(1, 2, 2),
(1, 3, 3),
(1, 4, 4),
(1, 5, 5),
(1, 6, 6),
(1, 7, 7),
(1, 8, 8);

--tuyến 2: BX Miền Tây --> Chợ Lớn
INSERT INTO route_stops (route_id, stop_id, stop_order) VALUES
(2, 1, 1),
(2, 2, 2),
(2, 3, 3),
(2, 4, 4),
(2, 9, 5),
(2, 10, 6),
(2, 11, 7),
(2, 12, 8);


--tuyến 3: BX Miền Đông --> An Sương
INSERT INTO route_stops (route_id, stop_id, stop_order) VALUES
(3, 13, 1),
(3, 14, 2),
(3, 5, 3),
(3, 6, 4),
(3, 7, 5),
(3, 8, 6);


--tuyến 4: CV Gia Định --> Chợ Lớn
INSERT INTO route_stops (route_id, stop_id, stop_order) VALUES
(4, 5, 1),
(4, 6, 2),
(4, 4, 3),
(4, 9, 4),
(4, 10, 5),
(4, 11, 6),
(4, 12, 7);

--thêm xe, tuyến 1 sẽ có 2 xe
INSERT INTO buses (bus_id, route_id) VALUES
('01', 1),
('02', 1),
('03', 2),
('04', 3),
('05', 4);
