from manim import *

class BackpropSignalFlow(Scene):
    def construct(self):
        title = Text("Backpropagation Through a Small Network", font_size=38).to_edge(UP)

        inputs = VGroup(*[Circle(radius=0.18, color=BLUE_D, fill_opacity=0.18) for _ in range(3)]).arrange(DOWN, buff=0.55).shift(LEFT * 4)
        hidden = VGroup(*[Circle(radius=0.18, color=TEAL_D, fill_opacity=0.18) for _ in range(4)]).arrange(DOWN, buff=0.5)
        outputs = VGroup(*[Circle(radius=0.18, color=PURPLE_D, fill_opacity=0.18) for _ in range(2)]).arrange(DOWN, buff=0.8).shift(RIGHT * 4)
        hidden.move_to(ORIGIN)
        input_labels = VGroup(*[Text(label, font_size=22).next_to(node, LEFT) for label, node in zip(["x1", "x2", "x3"], inputs)])
        output_labels = VGroup(*[Text(label, font_size=22).next_to(node, RIGHT) for label, node in zip(["y1", "y2"], outputs)])

        forward_1 = VGroup(*[Arrow(inp.get_right(), hid.get_left(), buff=0.08, stroke_width=2.5, color=GRAY_B) for inp in inputs for hid in hidden])
        forward_2 = VGroup(*[Arrow(hid.get_right(), out.get_left(), buff=0.08, stroke_width=2.5, color=GRAY_B) for hid in hidden for out in outputs])
        loss_box = RoundedRectangle(corner_radius=0.1, width=1.4, height=0.7, color=RED_D, fill_opacity=0.14).next_to(outputs, RIGHT, buff=1.0)
        loss_label = Text("loss", font_size=26, color=RED_D).move_to(loss_box)
        loss_arrows = VGroup(*[Arrow(out.get_right(), loss_box.get_left(), buff=0.08, stroke_width=3, color=RED_D) for out in outputs])

        backward_2 = VGroup(*[Arrow(out.get_left(), hid.get_right(), buff=0.08, stroke_width=3, color=ORANGE, max_tip_length_to_length_ratio=0.2) for out in outputs for hid in hidden])
        backward_1 = VGroup(*[Arrow(hid.get_left(), inp.get_right(), buff=0.08, stroke_width=3, color=YELLOW_D, max_tip_length_to_length_ratio=0.2) for hid in hidden for inp in inputs])
        update_panel = VGroup(
            RoundedRectangle(corner_radius=0.1, width=3.2, height=1.0, color=GREEN_D, fill_opacity=0.12),
            Text("weights shift opposite the gradient", font_size=24, color=GREEN_D),
        ).arrange(DOWN, buff=0.18).to_edge(DOWN)

        forward_caption = Text("Forward pass builds predictions", font_size=28, color=GRAY_D).to_edge(DOWN)
        loss_caption = Text("The loss compares prediction and target", font_size=28, color=RED_D).to_edge(DOWN)
        backward_caption = Text("Gradients flow backward to assign credit and blame", font_size=28, color=ORANGE).to_edge(DOWN)

        self.play(FadeIn(title), LaggedStart(*[FadeIn(node) for node in inputs], lag_ratio=0.1), LaggedStart(*[FadeIn(node) for node in hidden], lag_ratio=0.08), LaggedStart(*[FadeIn(node) for node in outputs], lag_ratio=0.12), FadeIn(input_labels), FadeIn(output_labels), run_time=5)
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in forward_1], lag_ratio=0.04), run_time=4)
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in forward_2], lag_ratio=0.05), FadeIn(forward_caption), run_time=4)
        self.wait(1)
        self.play(FadeIn(loss_box), FadeIn(loss_label), LaggedStart(*[GrowArrow(arrow) for arrow in loss_arrows], lag_ratio=0.15), ReplacementTransform(forward_caption, loss_caption), run_time=4)
        self.wait(1)
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in backward_2], lag_ratio=0.03), run_time=5)
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in backward_1], lag_ratio=0.03), ReplacementTransform(loss_caption, backward_caption), run_time=5)
        self.play(FadeIn(update_panel), run_time=3)
        self.wait(3)
