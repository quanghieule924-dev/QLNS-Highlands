from datetime import date

from django.db import transaction
from employees.models import NhanVien
from training.models import LichThi, DeThi, CauHoi


# Mỗi dòng:
# (Câu hỏi, phương án A, B, C, D, đáp án đúng)

NGAN_HANG = {

    # ======================================
    # 1. NGÂN HÀNG PHỤC VỤ - 20 CÂU
    # ======================================

    'Phục vụ': {
        'ma_lich': 'BANKLT001',
        'ma_de': 'BANKPV001',
        'tien_to': 'BANKPVQ',
        'cau_hoi': [
            (
                'Khi khách vừa vào cửa hàng, bạn nên làm gì?',
                'Chờ khách tự tìm chỗ',
                'Chủ động chào và hướng dẫn khách',
                'Yêu cầu khách đặt món ngay',
                'Chỉ chào khi khách gọi',
                'B'
            ),
            (
                'Trước khi mang đồ uống đến bàn, cần kiểm tra gì?',
                'Chỉ kiểm tra màu ly',
                'Chỉ kiểm tra tên nhân viên',
                'Đúng món và đúng khách hoặc số bàn',
                'Không cần kiểm tra',
                'C'
            ),
            (
                'Khách phản ánh đồ uống không đúng yêu cầu, bạn nên?',
                'Lắng nghe, xin lỗi và phối hợp xử lý',
                'Tranh luận với khách',
                'Bỏ qua vì cửa hàng đông',
                'Yêu cầu khách tự giải quyết',
                'A'
            ),
            (
                'Sàn khu vực phục vụ bị đổ nước, bạn cần?',
                'Chờ đến hết ca',
                'Để khách tự tránh',
                'Bỏ qua vì không phải việc mình',
                'Cảnh báo nguy cơ trượt và xử lý ngay',
                'D'
            ),
            (
                'Khi bàn giao ca, nhân viên phục vụ cần?',
                'Rời đi ngay khi hết giờ',
                'Kiểm tra vệ sinh và bàn giao công việc',
                'Để lại toàn bộ cho ca sau',
                'Chỉ chào đồng nghiệp',
                'B'
            ),
            (
                'Khi không chắc khách đã gọi món gì, bạn nên?',
                'Đoán món theo bàn bên cạnh',
                'Mang món bất kỳ ra trước',
                'Đối chiếu đơn và hỏi lại khi cần',
                'Bỏ qua đơn hàng',
                'C'
            ),
            (
                'Khách lớn tuổi cần hỗ trợ tìm chỗ ngồi, bạn nên?',
                'Lịch sự hướng dẫn đến chỗ phù hợp',
                'Đề nghị khách tự tìm',
                'Yêu cầu khách đứng chờ lâu',
                'Không trả lời khách',
                'A'
            ),
            (
                'Khi thu dọn bàn vừa có khách rời đi, cần?',
                'Chỉ gom ly thật nhanh',
                'Để nguyên đến cuối ngày',
                'Dùng chung khăn bẩn cho mọi bàn',
                'Thu dọn an toàn và vệ sinh đúng hướng dẫn',
                'D'
            ),
            (
                'Khách hỏi thành phần món mà bạn chưa rõ, nên?',
                'Tự đoán để trả lời',
                'Kiểm tra thông tin hoặc hỏi người phụ trách',
                'Nói mọi món đều giống nhau',
                'Bỏ qua câu hỏi',
                'B'
            ),
            (
                'Khi mang khay nhiều ly, hành động nào an toàn?',
                'Chạy thật nhanh',
                'Xếp quá nhiều ly lên khay',
                'Giữ khay cân bằng và di chuyển cẩn thận',
                'Vừa đi vừa dùng điện thoại',
                'C'
            ),
            (
                'Nếu khách làm đổ đồ uống tại bàn, bạn nên?',
                'Hỏi thăm và hỗ trợ xử lý',
                'Cười vì tình huống bất ngờ',
                'Bỏ mặc khách',
                'Đổ lỗi cho người pha chế',
                'A'
            ),
            (
                'Trong giờ cao điểm, nên giao tiếp với khách chờ thế nào?',
                'Không quan tâm hàng chờ',
                'Luôn hứa món sẽ có ngay',
                'Yêu cầu khách không hỏi',
                'Thông báo lịch sự và cập nhật khi có thông tin',
                'D'
            ),
            (
                'Khi khách bỏ quên đồ tại bàn, bạn nên?',
                'Giữ riêng để sử dụng',
                'Báo phụ trách và xử lý theo quy trình',
                'Tự ý mang về',
                'Đưa cho một người lạ',
                'B'
            ),
            (
                'Khi phục vụ đồ uống nóng, cần chú ý?',
                'Không cần nhắc khách',
                'Đặt sát mép bàn',
                'Cảnh báo nóng và đặt tại vị trí an toàn',
                'Đưa ngay cho trẻ nhỏ',
                'C'
            ),
            (
                'Khi cửa hàng không còn bàn trống, bạn nên?',
                'Giải thích lịch sự và đề xuất phương án phù hợp',
                'Từ chối nói chuyện',
                'Bảo khách tự giải quyết',
                'Tự ý giữ bàn cho bạn bè',
                'A'
            ),
            (
                'Khách yêu cầu hóa đơn, nhân viên phục vụ nên?',
                'Nói khách không cần hóa đơn',
                'Tự viết số tiền bất kỳ',
                'Bỏ qua yêu cầu',
                'Phối hợp với thu ngân để hỗ trợ',
                'D'
            ),
            (
                'Nếu phát hiện dụng cụ phục vụ bị nứt vỡ?',
                'Tiếp tục sử dụng',
                'Ngừng sử dụng và báo người phụ trách',
                'Che phần nứt lại',
                'Đưa cho khách dùng trước',
                'B'
            ),
            (
                'Khi khách đang nói chuyện điện thoại, bạn nên?',
                'Nói thật to để khách chú ý',
                'Liên tục ngắt lời khách',
                'Tiếp cận lịch sự và tôn trọng không gian',
                'Tự ý cầm điện thoại khách',
                'C'
            ),
            (
                'Khi đồng nghiệp cần hỗ trợ lúc đông khách?',
                'Phối hợp hỗ trợ trong phạm vi công việc',
                'Mặc kệ dù đang rảnh',
                'Chỉ trích đồng nghiệp trước mặt khách',
                'Rời khỏi khu vực',
                'A'
            ),
            (
                'Trước khi kết thúc lượt phục vụ, bạn nên?',
                'Đi ngay không cần quan sát',
                'Tự ý thu dọn khi khách đang dùng',
                'Cắt ngang cuộc trò chuyện',
                'Xác nhận khách đã nhận đủ món',
                'D'
            ),
        ]
    },

    # ======================================
    # 2. NGÂN HÀNG PHA CHẾ - 20 CÂU
    # ======================================

    'Pha chế': {
        'ma_lich': 'BANKLT002',
        'ma_de': 'BANKPC001',
        'tien_to': 'BANKPCQ',
        'cau_hoi': [
            (
                'Trước khi pha chế, thao tác quan trọng là?',
                'Vệ sinh tay và kiểm tra khu vực làm việc',
                'Pha ngay không cần kiểm tra',
                'Chỉ kiểm tra điện thoại',
                'Bỏ qua dụng cụ',
                'A'
            ),
            (
                'Khách yêu cầu ít đường, bạn nên?',
                'Bỏ qua yêu cầu',
                'Pha theo công thức thông thường',
                'Đối chiếu đơn và thực hiện đúng yêu cầu hợp lệ',
                'Tự ý đổi sang món khác',
                'C'
            ),
            (
                'Nguyên liệu có dấu hiệu hỏng, bạn cần?',
                'Tiếp tục sử dụng',
                'Ngừng sử dụng và báo phụ trách',
                'Trộn với nguyên liệu mới',
                'Cất lại đến ca sau',
                'B'
            ),
            (
                'Trước khi giao đồ uống, nên kiểm tra?',
                'Chỉ màu sắc',
                'Chỉ kích thước ly',
                'Không cần kiểm tra',
                'Tên món, yêu cầu tùy chỉnh và chất lượng',
                'D'
            ),
            (
                'Sau khi sử dụng dụng cụ pha chế, cần?',
                'Vệ sinh và đặt lại đúng vị trí',
                'Để nguyên trên quầy',
                'Chỉ lau sơ qua',
                'Đợi đến ngày hôm sau',
                'A'
            ),
            (
                'Khi nhận hai đơn có yêu cầu khác nhau, nên?',
                'Làm cả hai giống nhau',
                'Bỏ qua ghi chú',
                'Đối chiếu từng đơn để tránh nhầm',
                'Đoán theo khách',
                'C'
            ),
            (
                'Khi thấy ly có vết nứt, bạn cần?',
                'Sử dụng tạm',
                'Ngừng sử dụng và báo phụ trách',
                'Dán băng keo lại',
                'Đưa cho khách dùng trước',
                'B'
            ),
            (
                'Khu vực pha chế bị đổ nguyên liệu, nên?',
                'Tiếp tục làm việc trên chỗ đổ',
                'Đợi đến cuối ngày',
                'Để đồng nghiệp tự xử lý',
                'Cảnh báo và vệ sinh theo quy trình an toàn',
                'D'
            ),
            (
                'Khi chưa rõ cách làm món mới, bạn nên?',
                'Hỏi hướng dẫn hoặc kiểm tra công thức chuẩn',
                'Tự thử công thức bất kỳ',
                'Để khách tự chọn nguyên liệu',
                'Không làm và không báo',
                'A'
            ),
            (
                'Khi có nguy cơ dị ứng thành phần đồ uống, cần?',
                'Cam kết an toàn dù chưa kiểm tra',
                'Bỏ qua thông tin',
                'Kiểm tra thành phần và hỏi người phụ trách',
                'Tự ý thay nguyên liệu',
                'C'
            ),
            (
                'Cách bảo quản nguyên liệu phù hợp nhất là?',
                'Để bất kỳ nơi nào thuận tiện',
                'Tuân thủ nhãn và điều kiện bảo quản',
                'Trộn nguyên liệu cũ mới tùy ý',
                'Không cần kiểm tra',
                'B'
            ),
            (
                'Khi thiết bị pha chế hoạt động bất thường?',
                'Tự tháo máy khi chưa được đào tạo',
                'Tiếp tục sử dụng',
                'Bỏ qua tiếng kêu lạ',
                'Dừng sử dụng khi cần và báo phụ trách',
                'D'
            ),
            (
                'Một đơn có ghi chú không đá, bạn cần?',
                'Đọc kỹ và thực hiện theo ghi chú hợp lệ',
                'Cho nhiều đá hơn',
                'Bỏ ghi chú khi đông khách',
                'Chuyển sang món khác',
                'A'
            ),
            (
                'Tại sao cần giữ bề mặt pha chế sạch?',
                'Chỉ để quản lý nhìn thấy',
                'Để khỏi cần vệ sinh cuối ca',
                'Giảm nhiễm bẩn và thao tác an toàn',
                'Để đặt đồ dùng cá nhân',
                'C'
            ),
            (
                'Nếu món vừa pha không đạt chất lượng, nên?',
                'Giao ngay để kịp giờ',
                'Báo và xử lý theo quy trình',
                'Che phần lỗi',
                'Đổ lỗi cho thu ngân',
                'B'
            ),
            (
                'Khi bàn giao quầy pha chế, cần thông tin?',
                'Chỉ số điện thoại khách',
                'Danh sách nhạc',
                'Kế hoạch nghỉ cá nhân',
                'Tình trạng nguyên liệu, thiết bị và đơn đang xử lý',
                'D'
            ),
            (
                'Trước khi dùng nguyên liệu đóng gói, cần?',
                'Kiểm tra nhãn và hạn sử dụng',
                'Dùng hết nguyên liệu bất kể hạn',
                'Bỏ nhãn cho gọn',
                'Chỉ kiểm tra màu sắc',
                'A'
            ),
            (
                'Nếu khách hỏi món không có trên menu, nên?',
                'Cam kết làm bất kỳ món nào',
                'Bỏ qua khách',
                'Trao đổi phương án thay thế phù hợp',
                'Tự thu thêm tiền ngoài hệ thống',
                'C'
            ),
            (
                'Cách hạn chế nhầm lẫn khi pha nhiều đơn?',
                'Chỉ ghi nhớ mà không đối chiếu',
                'Theo dõi mã đơn và kiểm tra trước khi giao',
                'Đặt các đơn lẫn nhau',
                'Làm đơn ngẫu nhiên',
                'B'
            ),
            (
                'Khi thấy đồng nghiệp thao tác vệ sinh chưa đúng?',
                'Chụp ảnh đăng mạng',
                'Mặc kệ',
                'Tranh cãi trước mặt khách',
                'Nhắc nhở phù hợp và báo phụ trách khi cần',
                'D'
            ),
        ]
    },

    # ======================================
    # 3. NGÂN HÀNG THU NGÂN - 20 CÂU
    # ======================================

    'Thu ngân': {
        'ma_lich': 'BANKLT003',
        'ma_de': 'BANKTN001',
        'tien_to': 'BANKTNQ',
        'cau_hoi': [
            (
                'Trước khi xác nhận đơn, thu ngân cần?',
                'Thanh toán ngay',
                'Đối chiếu món, số lượng và tổng tiền',
                'Bỏ qua yêu cầu của khách',
                'Chỉ kiểm tra tên khách',
                'B'
            ),
            (
                'Khi khách thanh toán tiền mặt, cần?',
                'Nhận tiền mà không kiểm tra',
                'Bỏ qua tiền thừa',
                'Kiểm tra tiền nhận và trả tiền thừa đúng',
                'Nhờ khách tự tính',
                'C'
            ),
            (
                'Nhập sai món vào đơn, bạn nên?',
                'Kiểm tra và điều chỉnh theo quy trình',
                'Bỏ qua vì đã nhập',
                'Tự ý thu thêm tiền',
                'Không thông báo cho khách',
                'A'
            ),
            (
                'Máy thanh toán gặp sự cố, bạn nên?',
                'Thu tiền mà không ghi nhận',
                'Tắt máy và bỏ qua',
                'Đổ lỗi cho khách',
                'Thông báo và xử lý theo hướng dẫn',
                'D'
            ),
            (
                'Khi bàn giao ca thu ngân, cần?',
                'Rời quầy ngay',
                'Đối soát và bàn giao theo quy trình',
                'Chỉ nhớ số tiền trong đầu',
                'Để ca sau tự kiểm tra',
                'B'
            ),
            (
                'Khách muốn kiểm tra lại tổng hóa đơn, bạn nên?',
                'Từ chối vì hệ thống luôn đúng',
                'Yêu cầu khách tự tính',
                'Đối chiếu đơn và giải thích rõ ràng',
                'Xóa đơn ngay',
                'C'
            ),
            (
                'Thanh toán điện tử chưa báo thành công, nên?',
                'Kiểm tra trạng thái giao dịch trước khi xác nhận',
                'Nói đã thành công dù chưa kiểm tra',
                'Thu lại tiền ngay mà không đối chiếu',
                'Bỏ qua giao dịch',
                'A'
            ),
            (
                'Khi khách hỏi ưu đãi đang áp dụng, cần?',
                'Tự nghĩ ra khuyến mãi',
                'Áp dụng mọi ưu đãi không điều kiện',
                'Trả lời qua loa',
                'Kiểm tra chính sách và điều kiện hiện hành',
                'D'
            ),
            (
                'Để tránh nhập sai đơn lúc đông khách, nên?',
                'Nhập nhanh và bỏ qua kiểm tra',
                'Xác nhận thông tin trước khi thanh toán',
                'Dùng đơn của khách trước',
                'Không nghe ghi chú riêng',
                'B'
            ),
            (
                'Khi hóa đơn có giảm giá, thu ngân cần?',
                'Tự ý giảm thêm',
                'Bỏ qua thông tin',
                'Kiểm tra điều kiện và số tiền sau giảm',
                'Không cho khách kiểm tra',
                'C'
            ),
            (
                'Khách đổi phương thức thanh toán trước khi hoàn tất?',
                'Hướng dẫn và cập nhật theo quy trình',
                'Tự ý hủy mà không thông báo',
                'Từ chối mọi trường hợp',
                'Thu bằng cả hai phương thức',
                'A'
            ),
            (
                'Phát hiện chênh lệch tiền cuối ca, bạn nên?',
                'Bỏ tiền riêng bù mà không báo',
                'Giấu chênh lệch',
                'Tự sửa số liệu',
                'Đối soát và báo quản lý theo quy trình',
                'D'
            ),
            (
                'Khi khách đặt nhiều món giống nhau, cần?',
                'Chỉ nhập một món',
                'Xác nhận đúng số lượng từng món',
                'Tự tăng số lượng',
                'Không cần đọc lại đơn',
                'B'
            ),
            (
                'Thông tin thanh toán của khách cần được?',
                'Chia sẻ công khai',
                'Chụp lại lưu trên máy cá nhân',
                'Giữ bảo mật và sử dụng đúng mục đích',
                'Gửi cho bạn bè',
                'C'
            ),
            (
                'Khách đổi ý trước khi xác nhận đơn, nên?',
                'Cập nhật đơn và xác nhận lại với khách',
                'Giữ nguyên đơn cũ',
                'Thu thêm phí ngoài chính sách',
                'Không trả lời',
                'A'
            ),
            (
                'Để xuất hóa đơn đúng thông tin, bạn cần?',
                'Tự điền tùy ý',
                'Bỏ qua yêu cầu',
                'Dùng thông tin của khách trước',
                'Xác minh thông tin theo quy trình',
                'D'
            ),
            (
                'Khách phản ánh bị thanh toán trùng, nên?',
                'Bác bỏ ngay',
                'Kiểm tra lịch sử giao dịch và phối hợp xử lý',
                'Tự trả tiền từ két không ghi nhận',
                'Bỏ mặc khách',
                'B'
            ),
            (
                'Khi nhận tiền mặt, cách đếm tiền phù hợp?',
                'Không cần đếm',
                'Chỉ nhìn mệnh giá lớn nhất',
                'Đếm và đối chiếu cẩn thận',
                'Nhờ khách tự trả tiền thừa',
                'C'
            ),
            (
                'Khi hệ thống POS mất kết nối, bạn cần?',
                'Tuân thủ hướng dẫn dự phòng của cửa hàng',
                'Tự ghi doanh thu ngoài hệ thống',
                'Bấm liên tục mà không kiểm tra',
                'Cho khách đi mà không xử lý đơn',
                'A'
            ),
            (
                'Trước khi kết thúc giao dịch, thu ngân nên?',
                'Tắt màn hình ngay',
                'Không thông báo tổng tiền',
                'Vội vàng nhận khách tiếp theo',
                'Xác nhận thanh toán và hỗ trợ chứng từ',
                'D'
            ),
        ]
    }
}


# ======================================
# HÀM LƯU 60 CÂU VÀO SQLITE
# ======================================

@transaction.atomic
def nhap_du_lieu():

    # LichThi bắt buộc gắn với nhân viên.
    # Ưu tiên NV013, nếu không có sẽ lấy
    # một hồ sơ nhân viên đang tồn tại.
    nhan_vien = (
        NhanVien.objects.filter(manv='NV013').first()
        or NhanVien.objects.order_by('manv').first()
    )

    if nhan_vien is None:
        raise ValueError(
            'Chưa có nhân viên nào trong database.'
        )

    for vi_tri, data in NGAN_HANG.items():

        if len(data['cau_hoi']) != 20:
            raise ValueError(
                f'Ngân hàng {vi_tri} chưa đủ 20 câu.'
            )

        # 1. Lịch nguồn kỹ thuật
        lich, tao_moi = LichThi.objects.get_or_create(
            ma_lt=data['ma_lich'],
            defaults={
                'ma_nv': nhan_vien,
                'ngay_thi': date(2099, 1, 1),
                'ca_thi': 'BANK'
            }
        )

        if not tao_moi and (
            lich.ca_thi != 'BANK'
            or lich.ngay_thi != date(2099, 1, 1)
        ):
            raise ValueError(
                f'Mã {data["ma_lich"]} đã dùng '
                f'cho lịch khác.'
            )

        # 2. Đề nguồn
        de, tao_moi = DeThi.objects.get_or_create(
            ma_dt=data['ma_de'],
            defaults={
                'ma_lt': lich,
                'ten_de_thi': f'Ngân hàng câu hỏi {vi_tri}',
                'thoi_luong': 30
            }
        )

        if de.ma_lt_id != lich.ma_lt:
            raise ValueError(
                f'Mã đề {de.ma_dt} liên kết sai lịch.'
            )

        # 3. Nhập câu hỏi
        for stt, cau in enumerate(
            data['cau_hoi'], start=1
        ):
            noi_dung, a, b, c, d, dap_an = cau

            van_ban = (
                f'{noi_dung}\n'
                f'A. {a}\n'
                f'B. {b}\n'
                f'C. {c}\n'
                f'D. {d}'
            )

            ma_cau = f'{data["tien_to"]}{stt:03d}'

            CauHoi.objects.update_or_create(
                ma_ch=ma_cau,
                defaults={
                    'ma_dt': de,
                    'noi_dung_ch': van_ban,
                    'dap_an_dung': dap_an,
                    'diem': 5
                }
            )

        tong = CauHoi.objects.filter(
            ma_dt=de
        ).count()

        print(
            f'{vi_tri}: {tong} câu '
            f'| Mã nguồn: {de.ma_dt}'
        )

    print('HOÀN TẤT NHẬP NGÂN HÀNG CÂU HỎI')


nhap_du_lieu()
